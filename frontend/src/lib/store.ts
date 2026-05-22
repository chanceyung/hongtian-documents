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
  currentStep: number
  setCurrentStep: (step: number) => void

  apiKeys: ApiKeyConfig
  setApiKeys: (keys: Partial<ApiKeyConfig>) => void
  sessionId: string
  errors: string[]
  addError: (error: string) => void
  clearErrors: () => void

  uploadedFile: File | null
  setUploadedFile: (file: File | null) => void

  parseTask: ParseTask | null
  setParseTask: (task: ParseTask | null) => void

  magazineTask: MagazineTask | null
  setMagazineTask: (task: MagazineTask | null) => void
  fidelityReport: any
  setFidelityReport: (report: any) => void

  selectedTemplate: string
  setSelectedTemplate: (id: string) => void

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
  errors: [],
  addError: (error) => set((state) => ({ errors: [...state.errors, error] })),
  clearErrors: () => set({ errors: [] }),

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
