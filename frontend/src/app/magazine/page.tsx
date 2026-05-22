'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'
import { magazineApi } from '@/lib/api'
import { toast } from '@/components/ui/Toaster'

type Template = 'modern_tech' | 'elegant_minimal' | 'business_professional'
type ExportFormat = 'pdf' | 'pptx'

const templates: { id: Template; name: string; desc: string; colors: string; icon: string }[] = [
  { id: 'modern_tech', name: '现代科技', desc: '深色背景 + 科技蓝配色', colors: 'from-[#1a1a2e] to-[#0f3460]', icon: '01' },
  { id: 'elegant_minimal', name: '优雅极简', desc: '浅色背景 + 极简设计', colors: 'from-[#f8f9fa] to-[#dee2e6]', icon: '02' },
  { id: 'business_professional', name: '商务专业', desc: '深蓝背景 + 金色点缀', colors: 'from-[#0d1b2a] to-[#1b3a4b]', icon: '03' },
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
        } catch { }
        toast({ title: '杂志生成完成', variant: 'success' })
        return true
      }

      if (data.status === 'failed') {
        setStatus('failed')
        setStatusMsg(data.message || '处理失败')
        toast({ title: '生成失败', description: data.message || '处理过程中出现错误', variant: 'error' })
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

      try {
        const existingResp = await magazineApi.status(magazineTask.id)
        if (existingResp.data?.status === 'completed') {
          setStatus('completed')
          setProgress(100)
          setStatusMsg('已完成')
          setTaskId(magazineTask.id)
          return
        }
      } catch { }

      await magazineApi.generate(magazineTask.id, {
        outputFormat: format,
        templateId: selectedTpl,
      })

      setTaskId(magazineTask.id)
      setStatusMsg('等待处理...')
      toast({ title: '杂志生成任务已启动', variant: 'success' })
    } catch {
      setStatus('failed')
      setStatusMsg('连接失败，请检查后端服务')
      toast({ title: '启动失败', description: '无法连接后端服务', variant: 'error' })
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
      toast({ title: '下载成功', variant: 'success' })
    } catch {
      setStatusMsg('下载失败')
      toast({ title: '下载失败', description: '请重试或联系管理员', variant: 'error' })
    }
  }

  if (!magazineTask) return null

  return (
    <div className="page-container">
      <div className="glass-card p-5 mb-6 flex items-center gap-4 text-sm">
        <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center text-accent-light">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>
        <div>
          <span className="text-white font-medium">{magazineTask.fileName}</span>
          <span className="text-white/30 ml-3">{magazineTask.fileSize}</span>
        </div>
      </div>

      {status === 'idle' && (
        <div className="space-y-6 animate-fade-in-up">
          <div className="glass-card p-6">
            <h2 className="section-title">选择模板</h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {templates.map((tpl) => (
                <button
                  key={tpl.id}
                  onClick={() => setSelectedTpl(tpl.id)}
                  className={`p-4 rounded-xl border transition-all duration-300 text-left group ${
                    selectedTpl === tpl.id
                      ? 'border-accent/50 bg-accent/[0.06]'
                      : 'border-white/[0.06] hover:border-white/[0.12] bg-white/[0.02]'
                  }`}
                >
                  <div className={`w-full h-24 rounded-lg bg-gradient-to-br ${tpl.colors} mb-3 relative overflow-hidden`}>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-white/30 text-2xl font-bold">{tpl.icon}</span>
                    </div>
                  </div>
                  <h3 className="text-white font-medium">{tpl.name}</h3>
                  <p className="text-sm text-white/35 mt-1">{tpl.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div className="glass-card p-6">
            <h2 className="section-title">输出格式</h2>
            <div className="grid grid-cols-2 gap-4">
              {(['pdf', 'pptx'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFormat(f)}
                  className={`p-4 rounded-xl border transition-all duration-300 ${
                    format === f
                      ? 'border-accent/50 bg-accent/[0.06]'
                      : 'border-white/[0.06] hover:border-white/[0.12] bg-white/[0.02]'
                  }`}
                >
                  <div className="text-xl font-bold text-white/70 uppercase">{f}</div>
                  <p className="text-sm text-white/30 mt-1">
                    {f === 'pdf' ? '适合打印和分享' : '适合演示和编辑'}
                  </p>
                </button>
              ))}
            </div>
          </div>

          <button onClick={handleGenerate} className="btn-primary w-full py-4 text-base">
            开始生成
          </button>
        </div>
      )}

      {status === 'processing' && (
        <div className="glass-card p-10 animate-fade-in">
          <div className="flex flex-col items-center">
            <div className="relative mb-6">
              <div className="w-16 h-16 border-[3px] border-accent/20 border-t-accent rounded-full animate-spin" />
              <div className="absolute inset-0 w-16 h-16 border-[3px] border-transparent border-b-accent-light/30 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }} />
            </div>
            <p className="text-lg font-semibold text-white mb-2">{statusMsg}</p>
            <div className="w-full max-w-sm mt-4">
              <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-accent-dark via-accent to-accent-light transition-all duration-700 relative"
                  style={{ width: `${progress}%` }}
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" style={{ backgroundSize: '200% 100%' }} />
                </div>
              </div>
              <p className="text-sm text-white/30 mt-2 text-center">{progress}%</p>
            </div>
          </div>
        </div>
      )}

      {status === 'completed' && (
        <div className="space-y-4 animate-fade-in-up">
          <div className="glass-card p-10 text-center">
            <div className="w-16 h-16 bg-emerald-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-bold text-white mb-2">生成完成</h2>
            <p className="text-white/40">您的杂志文档已准备好</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button onClick={handleDownload} className="btn-primary w-full py-4">
              下载文档
            </button>
            <Link href={`/magazine/fidelity?task_id=${taskId}`} className="btn-secondary w-full py-4 text-center block">
              查看保真报告
            </Link>
          </div>
        </div>
      )}

      {status === 'failed' && (
        <div className="glass-card p-10 text-center animate-fade-in">
          <div className="w-16 h-16 bg-red-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-white mb-2">生成失败</h2>
          <p className="text-white/40 mb-6">{statusMsg}</p>
          <button onClick={handleGenerate} className="btn-primary">
            重试
          </button>
        </div>
      )}
    </div>
  )
}
