import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  timeout: 120000,
})

export const apiKeysApi = {
  save: (sessionId: string, keys: Record<string, string>) =>
    api.post('/api-keys/save', { session_id: sessionId, ...keys }),

  status: (sessionId: string) =>
    api.get(`/api-keys/status/${sessionId}`),

  testZhipu: (sessionId: string) =>
    api.post('/api-keys/test/zhipu?session_id=${sessionId}'),

  delete: (sessionId: string) =>
    api.delete(`/api-keys/${sessionId}`),
}

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
