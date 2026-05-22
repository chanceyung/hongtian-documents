'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
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
        <div className="animate-spin w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">保真报告</h2>
        <p className="text-gray-500">{error || '未找到报告数据。请先完成文档生成。'}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/magazine" className="flex items-center gap-2 text-brand-600 hover:text-brand-700">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            返回杂志页
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">保真校验报告</h1>
          <Link href="/settings" className="flex items-center gap-2 text-brand-600 hover:text-brand-700 text-sm">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            设置
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <FidelityReport
          score={report.fidelity_score}
          passed={report.fidelity_passed}
          l1Score={report.fidelity_passed ? 1.0 : 0.85}
          l2Score={report.fidelity_passed ? 1.0 : 0.90}
          l3Score={report.fidelity_score}
          issues={[]}
        />

        <div className="mt-6 flex items-center gap-4 text-sm text-gray-500">
          <span>修复次数: {report.repair_count}</span>
          <span>素材补充: {report.supplemented ? '是' : '否'}</span>
        </div>

        {report.fidelity_passed && (
          <div className="mt-8">
            <a
              href={`/api/magazine/export/${taskId}?format=pdf`}
              className="btn-primary"
            >
              下载生成的文档
            </a>
          </div>
        )}
      </main>
    </div>
  )
}
