'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
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
        <div className="flex justify-end gap-4 mb-4">
          <Link href="/history" className="flex items-center gap-2 text-brand-200 hover:text-white text-sm">
            历史记录
          </Link>
          <Link href="/settings" className="flex items-center gap-2 text-brand-200 hover:text-white text-sm">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            设置
          </Link>
        </div>
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
