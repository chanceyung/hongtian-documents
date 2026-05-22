import axios from 'axios'
import { getApiBaseUrl, runtimeMode } from './env'

// 创建 axios 实例（baseURL 将在 init 后确定）
const api = axios.create({
  timeout: 120000,
})

let _initialized = false

/**
 * 初始化 API 客户端。
 * Electron 模式下会等待获取后端端口。
 * 必须在 App 首次渲染时调用。
 */
export async function initApi(): Promise<void> {
  if (_initialized) return
  const baseUrl = await getApiBaseUrl()
  api.defaults.baseURL = baseUrl
  _initialized = true
  console.log(`[API] Base URL: ${baseUrl} (mode: ${runtimeMode})`)
}

export const apiKeyApi = {
  save: (config: {
    sessionId: string
    zhipuApiKey?: string
    zhipuModel?: string
    zhipuVisionKey?: string
    serpapiKey?: string
    fluxKey?: string
    fluxApiUrl?: string
  }) => api.post('/api-keys/save', {
    session_id: config.sessionId,
    zhipu_api_key: config.zhipuApiKey,
    zhipu_model: config.zhipuModel,
    zhipu_vision_key: config.zhipuVisionKey,
    serpapi_key: config.serpapiKey,
    flux_key: config.fluxKey,
    flux_api_url: config.fluxApiUrl,
  }),

  status: (sessionId: string) =>
    api.get(`/api-keys/status/${sessionId}`),

  testZhipu: (sessionId: string) =>
    api.post(`/api-keys/test/zhipu?session_id=${sessionId}`),

  delete: (sessionId: string) =>
    api.delete(`/api-keys/${sessionId}`),
}

export const magazineApi = {
  upload: (file: File, sessionId?: string) => {
    const formData = new FormData()
    formData.append('file', file)
    const params = sessionId ? { session_id: sessionId } : {}
    return api.post('/magazine/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params,
    })
  },
  generate: (taskId: string, options: { sessionId?: string; outputFormat?: string; templateId?: string }) =>
    api.post('/magazine/generate', {
      task_id: taskId,
      session_id: options.sessionId || '',
      output_format: options.outputFormat || 'pdf',
      template_id: options.templateId || 'modern_tech',
    }),
  status: (taskId: string) =>
    api.get(`/magazine/status/${taskId}`),
  fidelity: (taskId: string) =>
    api.get(`/magazine/fidelity/${taskId}`),
  export: (taskId: string, format: string) =>
    api.get(`/magazine/export/${taskId}`, { params: { format }, responseType: 'blob' }),
  listTasks: (sessionId: string) =>
    api.get('/magazine/tasks', { params: { session_id: sessionId } }),
  deleteTask: (taskId: string) =>
    api.delete(`/magazine/tasks/${taskId}`),
  eventsUrl: (taskId: string) =>
    `${api.defaults.baseURL}/magazine/events/${taskId}`,
  cleanup: (days: number = 7) =>
    api.post('/magazine/cleanup', null, { params: { days } }),
}

export default api