'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import FileUpload from '@/components/FileUpload'
import { useAppStore } from '@/lib/store'

const features = [
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
      </svg>
    ),
    title: 'AI 智能排版',
    desc: '五智能体协作，自动分析内容语义并生成杂志级排版',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
      </svg>
    ),
    title: '内容保真',
    desc: '四层校验流程确保原文内容 100% 还原，不增删改写',
  },
  {
    icon: (
      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
    ),
    title: '多格式支持',
    desc: '输入 PPTX/PDF/Word/Excel/MD，输出杂志品质 PDF 或 PPTX',
  },
]

const formats = [
  { ext: 'PPTX', label: '演示文稿' },
  { ext: 'PDF', label: '文档' },
  { ext: 'DOCX', label: 'Word' },
  { ext: 'XLSX', label: '表格' },
  { ext: 'MD', label: 'Markdown' },
]

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
    <div className="min-h-[calc(100vh-3.5rem)] bg-grid bg-radial-glow">
      <div className="container mx-auto px-4 py-20">
        <div className="max-w-3xl mx-auto text-center mb-14 animate-fade-in-up">
          <h1 className="text-5xl md:text-6xl font-bold mb-4">
            <span className="gradient-text">弘天文档</span>
          </h1>
          <p className="text-xl text-white/60 mb-3">
            杂志级文档重构智能体
          </p>
          <p className="text-white/35">
            上传文档，AI 自动完成解析、分析、排版、渲染、校验全流程
          </p>
        </div>

        <div className="max-w-2xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <div className="glass-card p-8 glow-border active">
            <FileUpload onUploadSuccess={handleUploadSuccess} />

            {error && (
              <p className="text-red-400 text-sm mt-4 text-center">{error}</p>
            )}
          </div>

          <div className="mt-6 flex items-center justify-center gap-2">
            <span className="text-white/25 text-xs">支持格式</span>
            <div className="flex gap-1.5">
              {formats.map((fmt) => (
                <span key={fmt.ext} className="badge bg-white/[0.06] text-white/40 border border-white/[0.06]">
                  {fmt.ext}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto mt-20 grid grid-cols-1 md:grid-cols-3 gap-5 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
          {features.map((feat) => (
            <div key={feat.title} className="glass-card-hover p-6">
              <div className="w-10 h-10 rounded-xl bg-accent/10 text-accent-light flex items-center justify-center mb-4">
                {feat.icon}
              </div>
              <h3 className="text-white font-semibold mb-2">{feat.title}</h3>
              <p className="text-sm text-white/40 leading-relaxed">{feat.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
