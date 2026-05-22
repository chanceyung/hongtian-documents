'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'
import { magazineApi } from '@/lib/api'
import { toast } from '@/components/ui/Toaster'

interface Task {
  task_id: string
  status: string
  progress: number
  message: string
  fidelity_score: number | null
  created_at: string
  output_format: string
}

const STATUS_MAP: Record<string, { label: string; color: string; bg: string }> = {
  pending: { label: '等待中', color: 'text-white/50', bg: 'bg-white/10' },
  parsing: { label: '解析中', color: 'text-accent-light', bg: 'bg-accent/20' },
  analyzing: { label: '分析中', color: 'text-accent-light', bg: 'bg-accent/20' },
  designing: { label: '设计中', color: 'text-accent-light', bg: 'bg-accent/20' },
  supplementing: { label: '补充素材', color: 'text-accent-light', bg: 'bg-accent/20' },
  rendering: { label: '渲染中', color: 'text-accent-light', bg: 'bg-accent/20' },
  verifying: { label: '校验中', color: 'text-accent-light', bg: 'bg-accent/20' },
  repairing: { label: '修复中', color: 'text-amber-300', bg: 'bg-amber-500/20' },
  finalizing: { label: '收尾中', color: 'text-accent-light', bg: 'bg-accent/20' },
  completed: { label: '已完成', color: 'text-emerald-300', bg: 'bg-emerald-500/20' },
  failed: { label: '失败', color: 'text-red-300', bg: 'bg-red-500/20' },
}

export default function HistoryPage() {
  const { sessionId } = useAppStore()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)

  const loadTasks = useCallback(async () => {
    try {
      const resp = await magazineApi.listTasks(sessionId)
      setTasks(resp.data)
    } catch {
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  useEffect(() => {
    const hasActive = tasks.some(t => !['completed', 'failed'].includes(t.status))
    if (!hasActive) return
    const timer = setInterval(loadTasks, 5000)
    return () => clearInterval(timer)
  }, [tasks, loadTasks])

  const handleDelete = async (taskId: string) => {
    try {
      await magazineApi.deleteTask(taskId)
      toast({ title: '任务已删除', variant: 'success' })
      await loadTasks()
    } catch (e: any) {
      toast({ title: '删除失败', description: e.response?.data?.detail, variant: 'error' })
    }
  }

  const handleDownload = async (taskId: string, format: string) => {
    try {
      const resp = await magazineApi.export(taskId, format)
      const url = URL.createObjectURL(resp.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `magazine_${taskId.slice(0, 8)}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      toast({ title: '下载失败', variant: 'error' })
    }
  }

  return (
    <div className="page-container">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold text-white">任务历史</h1>
          <Link href="/" className="nav-link">
            上传新文件
          </Link>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-8 h-8 border-2 border-accent/20 border-t-accent rounded-full animate-spin" />
          </div>
        ) : tasks.length === 0 ? (
          <div className="glass-card p-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-white/15" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <p className="text-white/30 mb-4">暂无任务记录</p>
            <Link href="/" className="text-accent-light hover:text-accent text-sm">
              上传文件开始
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map(task => {
              const info = STATUS_MAP[task.status] || { label: task.status, color: 'text-white/50', bg: 'bg-white/10' }
              return (
                <div key={task.task_id} className="glass-card-hover p-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-1.5">
                      <span className={`badge ${info.bg} ${info.color}`}>
                        {info.label}
                      </span>
                      <span className="text-xs text-white/25">
                        {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : ''}
                      </span>
                    </div>
                    <div className="text-sm text-white/50 truncate">
                      任务 {task.task_id.slice(0, 8)}
                      {task.fidelity_score != null && (
                        <span className="ml-3 text-white/25">保真度: {(task.fidelity_score * 100).toFixed(1)}%</span>
                      )}
                    </div>
                    {task.message && task.status === 'failed' && (
                      <div className="text-xs text-red-400/80 mt-1">{task.message}</div>
                    )}
                    {task.progress > 0 && task.progress < 1 && (
                      <div className="mt-2 w-full max-w-xs h-1 rounded-full bg-white/[0.06] overflow-hidden">
                        <div className="h-full rounded-full bg-gradient-to-r from-accent-dark to-accent-light transition-all" style={{ width: `${task.progress * 100}%` }} />
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4 shrink-0">
                    {task.status === 'completed' && (
                      <button onClick={() => handleDownload(task.task_id, 'pdf')} className="text-xs btn-primary px-3 py-1.5">
                        下载
                      </button>
                    )}
                    {task.status === 'failed' && (
                      <Link href={`/magazine?task_id=${task.task_id}`} className="text-xs px-3 py-1.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 transition-colors">
                        重试
                      </Link>
                    )}
                    <button onClick={() => handleDelete(task.task_id)} className="text-xs px-3 py-1.5 rounded-xl bg-white/[0.04] border border-white/[0.06] text-red-300/60 hover:bg-red-500/10 hover:border-red-500/20 hover:text-red-300 transition-colors">
                      删除
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
