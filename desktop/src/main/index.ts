/**
 * 弘天文档 — Electron 主进程
 */
import { app, BrowserWindow, Menu, shell, dialog, ipcMain } from 'electron'
import { join, resolve } from 'path'
import { ChildProcess, spawn } from 'child_process'
import { existsSync, mkdirSync } from 'fs'
import { platform } from 'os'
import * as net from 'net'

let mainWindow: BrowserWindow | null = null
let serverProcess: ChildProcess | null = null
let serverPort = 3000
let isQuitting = false

function findFreePort(startPort: number): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.listen(startPort, '127.0.0.1', () => {
      const addr = server.address()
      server.close(() => {
        if (addr && typeof addr === 'object') resolve(addr.port)
        else resolve(startPort)
      })
    })
    server.on('error', () => {
      if (startPort < 65535) resolve(findFreePort(startPort + 1))
      else reject(new Error('No available port'))
    })
  })
}

function getResourcesPath(): string {
  if (app.isPackaged) return join(process.resourcesPath, 'app')
  return resolve(__dirname, '..', '..')
}

function getUserDataDir(): string {
  const dir = join(app.getPath('userData'), 'data')
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true })
  return dir
}

function registerIpcHandlers(): void {
  ipcMain.handle('get-backend-port', () => serverPort)
  ipcMain.handle('app:getVersion', () => app.getVersion())
  ipcMain.handle('dialog:openFile', async (_event, filters) => {
    const result = await dialog.showOpenDialog(mainWindow!, {
      properties: ['openFile'],
      filters: filters || [],
    })
    return result.filePaths[0] || null
  })
  ipcMain.handle('window:minimize', () => mainWindow?.minimize())
  ipcMain.handle('window:maximize', () => {
    if (mainWindow?.isMaximized()) mainWindow.unmaximize()
    else mainWindow?.maximize()
  })
  ipcMain.handle('window:close', () => mainWindow?.close())
}

async function startServer(): Promise<void> {
  serverPort = await findFreePort(3000)

  const resPath = getResourcesPath()
  const dataDir = getUserDataDir()
  const bootScript = join(resPath, 'resources', 'app-server', 'boot.mjs')

  if (!existsSync(bootScript)) {
    throw new Error(`启动脚本不存在: ${bootScript}`)
  }

  const env: Record<string, string | undefined> = {
    ...process.env as Record<string, string>,
    NODE_ENV: 'production',
    DESKTOP_MODE: 'true',
    PORT: String(serverPort),
    DATABASE_PATH: join(dataDir, 'hongtian.db'),
  }
  Object.keys(env).forEach(k => { if (env[k] === undefined) delete env[k] })

  console.log(`[Main] Starting server on port ${serverPort}`)
  console.log(`[Main] Boot: ${bootScript}`)
  console.log(`[Main] DB: ${env.DATABASE_PATH}`)

  // 用系统 Node 而不是 Electron 的 Node（Electron 不支持 ESM）
  const nodeExe = platform() === 'win32' ? 'node' : 'node'
  serverProcess = spawn(nodeExe, [bootScript], {
    cwd: join(resPath, 'resources', 'app-server'),
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  serverProcess.stdout?.on('data', (data: Buffer) => {
    console.log(`[Server] ${data.toString().trim()}`)
  })

  serverProcess.stderr?.on('data', (data: Buffer) => {
    const msg = data.toString().trim()
    if (msg.includes('Error') || msg.includes('ECONNREFUSED')) {
      console.error(`[Server] ${msg}`)
    } else {
      console.log(`[Server] ${msg}`)
    }
  })

  serverProcess.on('error', (err) => {
    console.error(`[Main] Failed to start: ${err.message}`)
    dialog.showErrorBox('启动失败', `无法启动后端服务：${err.message}`)
  })

  serverProcess.on('exit', (code) => {
    if (!isQuitting) console.error(`[Server] exited with code ${code}`)
  })

  await waitForServer(serverPort, 15_000)
}

async function stopServer(): Promise<void> {
  if (!serverProcess || serverProcess.killed) return
  isQuitting = true
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      serverProcess?.kill('SIGKILL')
      resolve()
    }, 5000)
    serverProcess?.on('exit', () => { clearTimeout(timeout); resolve() })
    serverProcess?.kill('SIGTERM')
  })
}

async function waitForServer(port: number, timeout: number): Promise<void> {
  const start = Date.now()
  return new Promise((resolve, reject) => {
    function check() {
      if (Date.now() - start > timeout) { reject(new Error('Server startup timed out')); return }
      const socket = net.createConnection({ port, host: '127.0.0.1' }, () => {
        socket.destroy()
        console.log('[Main] Server ready')
        resolve()
      })
      socket.on('error', () => setTimeout(check, 500))
      socket.setTimeout(1000, () => { socket.destroy(); setTimeout(check, 500) })
    }
    check()
  })
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    title: '弘天文档',
    show: false,
    frame: false,
    webPreferences: {
      preload: join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  mainWindow.loadURL(`http://127.0.0.1:${serverPort}`)
  mainWindow.once('ready-to-show', () => mainWindow?.show())
  mainWindow.on('closed', () => { mainWindow = null })
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

function createMenu(): void {
  const template: Electron.MenuItemConstructorOptions[] = [
    { label: '文件', submenu: [
      { label: '打开文件...', accelerator: 'CmdOrCtrl+O', click: () => mainWindow?.webContents.send('menu:open-file') },
      { type: 'separator' },
      { label: '退出', accelerator: 'CmdOrCtrl+Q', role: 'quit' },
    ]},
    { label: '编辑', role: 'editMenu' },
    { label: '视图', submenu: [
      { role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' },
      { type: 'separator' },
      { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' },
      { type: 'separator' },
      { role: 'togglefullscreen' },
    ]},
    { label: '帮助', submenu: [{
      label: '关于弘天文档',
      click: () => { dialog.showMessageBoxSync(mainWindow!, {
        type: 'info', title: '关于弘天文档',
        message: `弘天文档 v${app.getVersion()}`,
        detail: '杂志级文档重构智能体\n将客户文档转化为杂志品质的 PDF / PPTX',
      })},
    }]},
  ]
  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

app.whenReady().then(async () => {
  try {
    registerIpcHandlers()
    Menu.setApplicationMenu(null)
    await startServer()
    createWindow()
  } catch (err) {
    console.error('[Main] Failed:', err)
    dialog.showErrorBox('启动失败', `应用启动失败：${err instanceof Error ? err.message : String(err)}`)
    app.quit()
  }
})

app.on('window-all-closed', () => { if (platform() !== 'darwin') app.quit() })
app.on('before-quit', async (e) => {
  if (serverProcess && !isQuitting) { e.preventDefault(); await stopServer(); app.quit() }
})
app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() })
