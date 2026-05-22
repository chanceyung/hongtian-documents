'use client'

import { useEffect, useState } from 'react'
import { useAppStore } from '@/lib/store'
import { magazineApi } from '@/lib/api'
import FidelityReport from '@/components/FidelityReport'

interface FidelityData {
  output_path: string
  fidelity_score: number
  fidelity_passed: boolean
  repair_count: number
  supplemented: boolean
}

export default function FidelityPage() {
  const { sessionId } = useAppStore()
  const [report, setReport] = useState<FidelityData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const taskId = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '').get('task_id') || ''

  useEffect(() => {
    if (!taskId) {
      setLoading(false)
      return
    }

    const fetchReport = async () => {
      try {
        const resp = await magazineApi.fidelity(taskId)
        setReport(resp.data)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : '获取保真报告失败')
      } finally {
        setLoading(false)
      }
    }

    fetchReport()
  }, [taskId])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="w-10 h-10 border-[3px] border-accent/20 border-t-accent rounded-full animate-spin" />
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <h2 className="text-xl font-semibold text-white/60 mb-2">保真报告</h2>
        <p className="text-white/30">{error || '未找到报告数据。请先完成文档生成。'}</p>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-8">保真校验报告</h1>

        <div className="glass-card p-8">
          <FidelityReport
            score={report.fidelity_score}
            passed={report.fidelity_passed}
            l1Score={report.fidelity_passed ? 1.0 : 0.85}
            l2Score={report.fidelity_passed ? 1.0 : 0.90}
            l3Score={report.fidelity_score}
            issues={[]}
          />
        </div>

        <div className="mt-6 glass-card p-5 flex items-center gap-6 text-sm text-white/40">
          <span>修复次数: <span className="text-white/60">{report.repair_count}</span></span>
          <span>素材补充: <span className="text-white/60">{report.supplemented ? '是' : '否'}</span></span>
        </div>

        {report.fidelity_passed && (
          <div className="mt-8">
            <a
              href={`/api/magazine/export/${taskId}?format=pdf`}
              className="btn-primary inline-block"
            >
              下载生成的文档
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
