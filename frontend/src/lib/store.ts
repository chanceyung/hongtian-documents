/**
 * 全局状态管理 - API Key 配置、任务状态、素材管理
 */
import { create } from 'zustand'

interface ApiKeyConfig {
  zhipuApiKey: string
  zhipuModel: string
  zhipuVisionKey: string
  serpApiKey: string
  fluxKey: string
  fluxApiUrl: string
}

interface ParseTask {
  taskId: string
  status: 'pending' | 'parsing' | 'linking' | 'completed' | 'failed'
  progress: number
  elementsCount: number
  imagesCount: number
  tablesCount: number
  error?: string
}

interface MagazineTask {
  id: string
  fileName: string
  fileSize: string
  status: 'pending' | 'parsing' | 'analyzing' | 'designing' | 'rendering' | 'verifying' | 'completed' | 'failed'
  progress: number
  fidelityScore: number | null
  error?: string
}

interface AppState {
  // 步骤控制
  currentStep: number
  setCurrentStep: (step: number) => void

  // API Key
  apiKeys: ApiKeyConfig
  setApiKeys: (keys: Partial<ApiKeyConfig>) => void
  sessionId: string

  // 文件上传
  uploadedFile: File | null
  setUploadedFile: (file: File | null) => void

  // 解析任务
  parseTask: ParseTask | null
  setParseTask: (task: ParseTask | null) => void

  // 杂志重构任务
  magazineTask: MagazineTask | null
  setMagazineTask: (task: MagazineTask | null) => void
  fidelityReport: any
  setFidelityReport: (report: any) => void

  // 排版模板
  selectedTemplate: string
  setSelectedTemplate: (id: string) => void

  // 导出格式
  outputFormat: 'pdf' | 'pptx'
  setOutputFormat: (format: 'pdf' | 'pptx') => void
}

export const useAppStore = create<AppState>((set) => ({
  currentStep: 0,
  setCurrentStep: (step) => set({ currentStep: step }),

  apiKeys: {
    zhipuApiKey: '',
    zhipuModel: 'glm-5-pro',
    zhipuVisionKey: '',
    serpApiKey: '',
    fluxKey: '',
    fluxApiUrl: '',
  },
  setApiKeys: (keys) =>
    set((state) => ({ apiKeys: { ...state.apiKeys, ...keys } })),
  sessionId: crypto.randomUUID?.() || Math.random().toString(36).slice(2),

  uploadedFile: null,
  setUploadedFile: (file) => set({ uploadedFile: file }),

  parseTask: null,
  setParseTask: (task) => set({ parseTask: task }),

  magazineTask: null,
  setMagazineTask: (task) => set({ magazineTask: task }),
  fidelityReport: null,
  setFidelityReport: (report) => set({ fidelityReport: report }),

  selectedTemplate: 'default',
  setSelectedTemplate: (id) => set({ selectedTemplate: id }),

  outputFormat: 'pdf',
  setOutputFormat: (format) => set({ outputFormat: format }),
}))
