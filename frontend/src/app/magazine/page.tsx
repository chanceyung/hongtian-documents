'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'
import { magazineApi } from '@/lib/api'

type Template = 'modern_tech' | 'elegant_minimal' | 'business_professional'
type ExportFormat = 'pdf' | 'pptx'

const templates: { id: Template; name: string; desc: string; colors: string }[] = [
  { id: 'modern_tech', name: '现代科技', desc: '深色背景 + 科技蓝配色', colors: 'from-[#1a1a2e] to-[#0f3460]' },
  { id: 'elegant_minimal', name: '优雅极简', desc: '浅色背景 + 极简设计', colors: 'from-[#f5f5f5] to-[#e0e0e0]' },
  { id: 'business_professional', name: '商务专业', desc: '深蓝背景 + 金色点缀', colors: 'from-[#0d1b2a] to-[#1b3a4b]' },
]

export default function MagazinePage() {
  const { magazineTask, setFidelityReport, setSelectedTemplate, setOutputFormat } = useAppStore()
  const router = useRouter()

  const [selectedTpl, setSelectedTpl] = useState<Template>('modern_tech')
  const [format, setFormat] = useState<ExportFormat>('pdf')
  const [status, setStatus] = useState<'idle' | 'processing' | 'completed' | 'failed'>('idle')
  const [progress, setProgress] = useState(0)
  const [statusMsg, setStatusMsg] = useState('')
  const [exportUrl, setExportUrl] = useState<string | null>(null)
  const [taskId, setTaskId] = useState<string | null>(null)

  useEffect(() => {
    if (!magazineTask) {
      router.push('/')
    }
  }, [magazineTask, router])

  useEffect(() => {
    return () => {
      if (exportUrl) URL.revokeObjectURL(exportUrl)
    }
  }, [exportUrl])

  const pollStatus = useCallback(async (id: string) => {
    try {
      const resp = await magazineApi.status(id)
      const data = resp.data

      const newProgress = Math.round((data.progress || 0) * 100)
      const statusMap: Record<string, string> = {
        pending: '等待处理', parsing: '解析文档', analyzing: '内容分析',
        designing: '排版设计', rendering: '渲染生成', verifying: '保真校验',
        completed: '已完成', failed: '处理失败',
      }
      const newMsg = statusMap[data.status] || data.status

      if (newProgress !== progress) setProgress(newProgress)
      if (newMsg !== statusMsg) setStatusMsg(newMsg)

      if (data.status === 'completed') {
        setStatus('completed')
        try {
          const report = await magazineApi.fidelity(id)
          setFidelityReport(report.data)
        } catch { /* report optional */ }
        return true
      }

      if (data.status === 'failed') {
        setStatus('failed')
        setStatusMsg(data.message || '处理失败')
        return true
      }

      return false
    } catch {
      return false
    }
  }, [setFidelityReport, progress, statusMsg])

  useEffect(() => {
    if (!taskId || status !== 'processing') return

    const interval = setInterval(async () => {
      const done = await pollStatus(taskId)
      if (done) clearInterval(interval)
    }, 2000)

    return () => clearInterval(interval)
  }, [taskId, status, pollStatus])

  const handleGenerate = async () => {
    if (!magazineTask) return

    setStatus('processing')
    setProgress(0)
    setStatusMsg('启动生成任务...')
    setSelectedTemplate(selectedTpl)
    setOutputFormat(format)

    try {
      if (exportUrl) {
        URL.revokeObjectURL(exportUrl)
        setExportUrl(null)
      }

      // 先检查是否已完成
      try {
        const existingResp = await magazineApi.status(magazineTask.id)
        if (existingResp.data?.status === 'completed') {
          setStatus('completed')
          setProgress(100)
          setStatusMsg('已完成')
          setTaskId(magazineTask.id)
          return
        }
      } catch { /* task may not exist yet */ }

      // 调用 generate 端点启动 pipeline
      await magazineApi.generate(magazineTask.id, {
        outputFormat: format,
        templateId: selectedTpl,
      })

      setTaskId(magazineTask.id)
      setStatusMsg('等待处理...')
    } catch {
      setStatus('failed')
      setStatusMsg('连接失败，请检查后端服务')
    }
  }

  const handleDownload = async () => {
    if (!taskId) return
    try {
      const resp = await magazineApi.export(taskId, format)
      const blob = new Blob([resp.data])
      const url = URL.createObjectURL(blob)
      setExportUrl(url)

      const a = document.createElement('a')
      a.href = url
      a.download = `magazine_${taskId.slice(0, 8)}.${format}`
      a.click()
    } catch {
      setStatusMsg('下载失败')
    }
  }

  if (!magazineTask) return null

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-brand-600 hover:text-brand-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            返回首页
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">生成杂志文档</h1>
          <div className="w-20" />
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="card mb-6">
          <div className="flex items-center gap-4 text-sm text-gray-600">
            <span>文件: <strong className="text-gray-900">{magazineTask.fileName}</strong></span>
            <span className="text-gray-300">|</span>
            <span>大小: {magazineTask.fileSize}</span>
          </div>
        </div>

        {status === 'idle' && (
          <div className="space-y-6 animate-fade-in">
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">选择模板</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {templates.map((tpl) => (
                  <button
                    key={tpl.id}
                    onClick={() => setSelectedTpl(tpl.id)}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${
                      selectedTpl === tpl.id
                        ? 'border-brand-500 bg-brand-50 shadow-sm'
                        : 'border-gray-200 hover:border-brand-300'
                    }`}
                  >
                    <div className={`w-full h-24 rounded-lg bg-gradient-to-br ${tpl.colors} mb-3`} />
                    <h3 className="font-semibold text-gray-900">{tpl.name}</h3>
                    <p className="text-sm text-gray-500 mt-1">{tpl.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">输出格式</h2>
              <div className="grid grid-cols-2 gap-4">
                {(['pdf', 'pptx'] as const).map((f) => (
                  <button
                    key={f}
                    onClick={() => setFormat(f)}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      format === f
                        ? 'border-brand-500 bg-brand-50'
                        : 'border-gray-200 hover:border-brand-300'
                    }`}
                  >
                    <div className="text-xl font-bold text-brand-600 uppercase">{f}</div>
                    <p className="text-sm text-gray-500 mt-1">
                      {f === 'pdf' ? '适合打印和分享' : '适合演示和编辑'}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            <button onClick={handleGenerate} className="btn-primary w-full py-4 text-lg">
              开始生成
            </button>
          </div>
        )}

        {status === 'processing' && (
          <div className="card animate-fade-in">
            <div className="flex flex-col items-center py-8">
              <div className="w-16 h-16 border-4 border-brand-500 border-t-transparent rounded-full animate-spin mb-6" />
              <p className="text-lg font-semibold text-gray-900 mb-2">{statusMsg}</p>
              <div className="w-full max-w-md bg-gray-200 rounded-full h-3 mt-4">
                <div
                  className="bg-brand-500 h-3 rounded-full transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-sm text-gray-500 mt-2">{progress}%</p>
            </div>
          </div>
        )}

        {status === 'completed' && (
          <div className="space-y-4 animate-fade-in">
            <div className="card text-center py-8">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-2">生成完成</h2>
              <p className="text-gray-500">您的杂志文档已准备好</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button onClick={handleDownload} className="btn-primary w-full py-4">
                下载文档
              </button>
              <Link href={`/magazine/fidelity?task_id=${taskId}`} className="btn-secondary w-full py-4 text-center">
                查看保真报告
              </Link>
            </div>
          </div>
        )}

        {status === 'failed' && (
          <div className="card text-center py-8 animate-fade-in">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">生成失败</h2>
            <p className="text-gray-500 mb-6">{statusMsg}</p>
            <button onClick={handleGenerate} className="btn-primary">
              重试
            </button>
          </div>
        )}
      </main>
    </div>
  )
}
