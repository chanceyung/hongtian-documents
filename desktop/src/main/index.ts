/**
 * 弘天文档 — Electron 主进程
 *
 * 职责：
 * 1. 启动/停止内嵌 Python 后端
 * 2. 管理应用窗口
 * 3. 处理系统托盘和菜单
 */
import { app, BrowserWindow, Menu, shell, dialog } from 'electron'
import { join, resolve } from 'path'
import { ChildProcess, spawn } from 'child_process'
import { existsSync, mkdirSync } from 'fs'
import { platform } from 'os'
import { findFreePort } from './port-utils'

// ─── Globals ────────────────────────────────────────────────────────────────
let mainWindow: BrowserWindow | null = null
let backendProcess: ChildProcess | null = null
let backendPort = 8000
let isQuitting = false

// ─── Paths ──────────────────────────────────────────────────────────────────
function getResourcesPath(): string {
  // 开发模式: desktop/resources
  // 生产模式: process.resourcesPath
  if (app.isPackaged) {
    return process.resourcesPath
  }
  return resolve(__dirname, '..', 'resources')
}

function getPythonExe(): string {
  const resPath = getResourcesPath()
  const isWin = platform() === 'win32'

  if (app.isPackaged) {
    return join(resPath, 'python', isWin ? 'python.exe' : 'bin/python')
  }

  // 开发模式：使用系统 Python 或指定路径
  const devPython = process.env.HONGTIAN_PYTHON || (isWin ? 'python' : 'python3')
  return devPython
}

function getBackendDir(): string {
  if (app.isPackaged) {
    return join(getResourcesPath(), 'python', 'app')
  }
  // 开发模式：直接引用 backend/app
  return resolve(__dirname, '..', '..', 'backend')
}

function getUserDataDir(): string {
  const dir = join(app.getPath('userData'), 'data')
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true })
  }
  return dir
}

// ─── Backend Management ─────────────────────────────────────────────────────
async function startBackend(): Promise<void> {
  backendPort = await findFreePort(8000)

  const pythonExe = getPythonExe()
  const backendDir = getBackendDir()
  const dataDir = getUserDataDir()

  const env = {
    ...process.env,
    DESKTOP_MODE: 'true',
    PYTHONUNBUFFERED: '1',
    PYTHONIOENCODING: 'utf-8',
    PORT: String(backendPort),
    DATABASE_URL: `sqlite:///${join(dataDir, 'magazine.db')}`,
    OUTPUT_DIR: join(dataDir, 'output'),
    UPLOAD_DIR: join(dataDir, 'uploads'),
    ASSETS_DIR: join(dataDir, 'assets'),
    APP_DATA_DIR: join(dataDir, 'app_data'),
    CORS_ORIGINS: `["http://localhost:${backendPort}"]`,
    PLAYWRIGHT_BROWSERS_PATH: app.isPackaged
      ? join(getResourcesPath(), 'python', 'playwright-browsers')
      : undefined,
  }

  // 清理未定义的 env 字段
  Object.keys(env).forEach(k => env[k] === undefined && delete env[k])

  console.log(`[Main] Starting backend on port ${backendPort}`)
  console.log(`[Main] Python: ${pythonExe}`)
  console.log(`[Main] Backend dir: ${backendDir}`)

  const args = [
    '-m', 'uvicorn',
    'app.main:app',
    '--host', '127.0.0.1',
    '--port', String(backendPort),
    '--workers', '1',
    '--log-level', 'info',
    '--no-access-log',
  ]

  backendProcess = spawn(pythonExe, args, {
    cwd: backendDir,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  backendProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[Backend] ${data.toString().trim()}`)
  })

  backendProcess.stderr?.on('data', (data: Buffer) => {
    console.error(`[Backend] ${data.toString().trim()}`)
  })

  backendProcess.on('exit', (code) => {
    if (!isQuitting) {
      console.error(`[Backend] exited with code ${code}`)
    }
  })

  // 等待后端就绪
  await waitForBackend(backendPort, 30_000)
}

async function stopBackend(): Promise<void> {
  if (!backendProcess) return

  isQuitting = true
  console.log('[Main] Stopping backend...')

  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      console.log('[Main] Force killing backend')
      backendProcess?.kill('SIGKILL')
      resolve()
    }, 5000)

    backendProcess?.on('exit', () => {
      clearTimeout(timeout)
      resolve()
    })

    backendProcess?.kill('SIGTERM')
  })
}

async function waitForBackend(port: number, timeout: number): Promise<void> {
  const start = Date.now()
  const http = await import('http')

  return new Promise((resolve, reject) => {
    function check() {
      if (Date.now() - start > timeout) {
        reject(new Error('Backend startup timed out'))
        return
      }

      const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
        if (res.statusCode === 200) {
          console.log('[Main] Backend ready')
          resolve()
        } else {
          setTimeout(check, 500)
        }
      })

      req.on('error', () => setTimeout(check, 500))
      req.end()
    }
    check()
  })
}

// ─── Window Management ──────────────────────────────────────────────────────
function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    title: '弘天文档',
    show: false,
    webPreferences: {
      preload: join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  // 加载前端页面
  if (app.isPackaged) {
    mainWindow.loadFile(join(getResourcesPath(), 'frontend', 'index.html'))
  } else {
    // 开发模式：加载前端 dev server 或静态文件
    const frontendUrl = process.env.FRONTEND_URL || `http://localhost:3000`
    mainWindow.loadURL(frontendUrl)
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show()
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  // 外部链接在浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

// ─── Application Menu ───────────────────────────────────────────────────────
function createMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: '文件',
      submenu: [
        { label: '打开文件...', accelerator: 'CmdOrCtrl+O', click: () => mainWindow?.webContents.send('menu:open-file') },
        { type: 'separator' },
        { label: '退出', accelerator: 'CmdOrCtrl+Q', click: () => app.quit() },
      ],
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
      ],
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: '关于弘天文档',
          click: () => {
            dialog.showMessageBoxSync(mainWindow!, {
              type: 'info',
              title: '关于弘天文档',
              message: `弘天文档 v${app.getVersion()}`,
              detail: '杂志级文档重构智能体\n将客户文档转化为杂志品质的 PDF / PPTX',
            })
          },
        },
      ],
    },
  ]

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

// ─── Preload ────────────────────────────────────────────────────────────────
// preload.js 需要单独编译，这里仅创建入口

// ─── App Lifecycle ──────────────────────────────────────────────────────────
app.whenReady().then(async () => {
  try {
    createMenu()
    await startBackend()
    createWindow()
  } catch (err) {
    console.error('[Main] Failed to start:', err)
    dialog.showErrorBox(
      '启动失败',
      `后端服务启动失败：${err instanceof Error ? err.message : String(err)}`,
    )
    app.quit()
  }
})

app.on('window-all-closed', () => {
  app.quit()
})

app.on('before-quit', async (e) => {
  if (backendProcess && !isQuitting) {
    e.preventDefault()
    await stopBackend()
    app.quit()
  }
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow()
  }
})