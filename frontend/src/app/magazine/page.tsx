'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'
import ProgressBar from '@/components/ProgressBar'
import { magazineApi } from '@/lib/api'

type Template = 'modern_tech' | 'elegant_minimal' | 'business_professional'

type ExportFormat = 'pdf' | 'pptx'

const templates = [
  {
    id: 'modern_tech' as Template,
    name: '现代科技',
    description: '科技感十足，适合技术文档',
    preview: '/templates/modern_tech.png',
  },
  {
    id: 'elegant_minimal' as Template,
    name: '优雅简约',
    description: '简洁大方，突出内容',
    preview: '/templates/elegant_minimal.png',
  },
  {
    id: 'business_professional' as Template,
    name: '商务专业',
    description: '正式专业，适合商务场景',
    preview: '/templates/business_professional.png',
  },
]

export default function MagazinePage() {
  const { magazineTask } = useAppStore()
  const [selectedTemplate, setSelectedTemplate] = useState<Template>('modern_tech')
  const [exportFormat, setExportFormat] = useState<ExportFormat>('pdf')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationProgress, setGenerationProgress] = useState(0)
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'processing' | 'completed' | 'failed'>('idle')
  const [exportUrl, setExportUrl] = useState<string | null>(null)

  const router = useRouter()

  useEffect(() => {
    if (!magazineTask) {
      router.push('/')
    }
  }, [magazineTask, router])

  const handleGenerate = async () => {
    if (!magazineTask) return

    setIsGenerating(true)
    setGenerationStatus('processing')
    setGenerationProgress(0)

    try {
      const response = await magazineApi.export(magazineTask.id, exportFormat)
      const blob = new Blob([response.data])
      const url = URL.createObjectURL(blob)
      setExportUrl(url)
      setGenerationStatus('completed')
      setGenerationProgress(100)
    } catch (error) {
      console.error('Failed to generate magazine:', error)
      setGenerationStatus('failed')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDownload = () => {
    if (!exportUrl || !magazineTask) return

    const link = document.createElement('a')
    link.href = exportUrl
    link.download = `magazine_${magazineTask.fileName}.${exportFormat}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  if (!magazineTask) {
    return null
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <Link
              href="/"
              className="inline-flex items-center text-brand-600 hover:text-brand-700 font-medium"
            >
              <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              返回首页
            </Link>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-3xl font-bold text-brand-900 mb-6">
              生成杂志文档
            </h1>

            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">选择模板</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => setSelectedTemplate(template.id)}
                    className={`p-4 rounded-lg border-2 transition-all ${
                      selectedTemplate === template.id
                        ? 'border-brand-500 bg-brand-50'
                        : 'border-gray-200 hover:border-brand-300'
                    }`}
                  >
                    <div className="w-full h-32 bg-gray-100 rounded-lg mb-3 flex items-center justify-center">
                      <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                    <h3 className="font-semibold text-gray-900 mb-1">{template.name}</h3>
                    <p className="text-sm text-gray-600">{template.description}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">选择输出格式</h2>
              <div className="flex space-x-4">
                <button
                  onClick={() => setExportFormat('pdf')}
                  className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                    exportFormat === 'pdf'
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-gray-200 hover:border-brand-300'
                  }`}
                >
                  <div className="text-2xl font-bold text-brand-600 mb-1">PDF</div>
                  <p className="text-sm text-gray-600">适合打印和分享</p>
                </button>
                <button
                  onClick={() => setExportFormat('pptx')}
                  className={`flex-1 p-4 rounded-lg border-2 transition-all ${
                    exportFormat === 'pptx'
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-gray-200 hover:border-brand-300'
                  }`}
                >
                  <div className="text-2xl font-bold text-brand-600 mb-1">PPTX</div>
                  <p className="text-sm text-gray-600">适合演示和编辑</p>
                </button>
              </div>
            </div>

            {generationStatus === 'idle' && (
              <button
                onClick={handleGenerate}
                className="w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors"
              >
                开始生成
              </button>
            )}

            {(generationStatus === 'processing' || generationStatus === 'completed' || generationStatus === 'failed') && (
              <div className="space-y-6">
                <ProgressBar
                  progress={generationProgress}
                  label={generationStatus === 'processing' ? '正在生成...' : generationStatus === 'completed' ? '生成完成' : '生成失败'}
                  status={generationStatus}
                />

                {generationStatus === 'completed' && (
                  <button
                    onClick={handleDownload}
                    className="w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors"
                  >
                    下载文档
                  </button>
                )}

                {generationStatus === 'failed' && (
                  <button
                    onClick={handleGenerate}
                    className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-4 px-6 rounded-lg transition-colors"
                  >
                    重试
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}