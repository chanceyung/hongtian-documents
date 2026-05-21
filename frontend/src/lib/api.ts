/**
 * API 调用封装
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// API Key 管理
export const apiKeysApi = {
  save: (sessionId: string, keys: Record<string, string>) =>
    api.post('/api-keys/save', { session_id: sessionId, ...keys }),

  status: (sessionId: string) =>
    api.get(`/api-keys/status/${sessionId}`),

  testZhipu: (sessionId: string) =>
    api.post(`/api-keys/test/zhipu?session_id=${sessionId}`),

  delete: (sessionId: string) =>
    api.delete(`/api-keys/${sessionId}`),
}

// 文档解析
export const parseApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/parse/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  status: (taskId: string) =>
    api.get(`/parse/status/${taskId}`),

  result: (taskId: string) =>
    api.get(`/parse/result/${taskId}`),
}

// 文档生成
export const generateApi = {
  generatePdf: (taskId: string, sessionId: string, templateId: string) =>
    api.post('/generate/pdf', {
      task_id: taskId,
      session_id: sessionId,
      template_id: templateId,
    }),

  generatePptx: (taskId: string, sessionId: string, templateId: string) =>
    api.post('/generate/pptx', {
      task_id: taskId,
      session_id: sessionId,
      template_id: templateId,
    }),
}

// 杂志重构 API
export const magazineApi = {
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/magazine/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  status: (taskId: string) =>
    api.get(`/magazine/status/${taskId}`),
  fidelity: (taskId: string) =>
    api.get(`/magazine/fidelity/${taskId}`),
  export: (taskId: string, format: string) =>
    api.get(`/magazine/export/${taskId}`, { params: { format }, responseType: 'blob' }),
}

export default api
