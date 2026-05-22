/**
 * 环境检测与 API 配置
 *
 * 桌面版 (Electron):
 *   - 后端自动启动在随机端口
 *   - 通过 window.electronAPI.getBackendPort() 获取
 *
 * Web 版:
 *   - 后端在固定 URL
 *   - 通过 NEXT_PUBLIC_API_URL 环境变量配置
 */

export type RuntimeMode = 'electron' | 'web'

function detectMode(): RuntimeMode {
  if (typeof window !== 'undefined' && window.electronAPI) {
    return 'electron'
  }
  return 'web'
}

export const runtimeMode: RuntimeMode = detectMode()

let _baseUrl = ''

export async function getApiBaseUrl(): Promise<string> {
  if (_baseUrl) return _baseUrl

  if (runtimeMode === 'electron') {
    const port = await window.electronAPI!.getBackendPort()
    _baseUrl = `http://127.0.0.1:${port}/api`
  } else {
    _baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
  }

  return _baseUrl
}

// 同步获取（已知已初始化后）
export function getApiBaseUrlSync(): string {
  if (_baseUrl) return _baseUrl
  if (runtimeMode === 'web') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api'
  }
  return 'http://127.0.0.1:8000/api' // fallback, 应先调用 getApiBaseUrl
}

// Electron API 类型声明
declare global {
  interface Window {
    electronAPI?: {
      getBackendPort: () => Promise<number>
      platform: string
      openFile: (filters: any) => Promise<string | null>
      getVersion: () => Promise<string>
    }
  }
}