'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import FileUpload from '@/components/FileUpload'
import { useAppStore } from '@/lib/store'

export default function Home() {
  const { setMagazineTask } = useAppStore()
  const [error, setError] = useState('')
  const router = useRouter()

  const handleUploadSuccess = (taskData: {
    id: string
    fileName: string
    fileSize: string
    status: 'pending' | 'parsing' | 'analyzing' | 'designing' | 'rendering' | 'verifying' | 'completed' | 'failed'
    progress: number
    fidelityScore: number | null
  }) => {
    setMagazineTask(taskData)
    router.push('/import')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-800 via-brand-700 to-brand-900">
      <div className="container mx-auto px-4 py-16">
        <div className="max-w-3xl mx-auto text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            弘天文档
          </h1>
          <p className="text-xl text-brand-100 mb-4">
            杂志级文档重构智能体
          </p>
          <p className="text-brand-200">
            将 PPTX、PDF、Word、Excel、Markdown 文档转化为杂志品质的 PDF 或 PPTX
          </p>
        </div>

        <div className="max-w-2xl mx-auto">
          <div className="bg-white/95 backdrop-blur rounded-2xl shadow-2xl p-8">
            <FileUpload onUploadSuccess={handleUploadSuccess} />

            {error && (
              <p className="text-red-600 text-sm mt-4 text-center">{error}</p>
            )}
          </div>

          <div className="mt-8 grid grid-cols-5 gap-3 text-center">
            {['PPTX', 'PDF', 'DOCX', 'XLSX', 'MD'].map((fmt) => (
              <div key={fmt} className="bg-white/10 rounded-lg py-2 text-brand-200 text-sm font-medium">
                {fmt}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
