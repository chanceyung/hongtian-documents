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

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'bg-gray-600' },
  parsing: { label: '解析中', color: 'bg-blue-600' },
  analyzing: { label: '分析中', color: 'bg-blue-600' },
  designing: { label: '设计中', color: 'bg-blue-600' },
  supplementing: { label: '补充素材', color: 'bg-blue-600' },
  rendering: { label: '渲染中', color: 'bg-blue-600' },
  verifying: { label: '校验中', color: 'bg-blue-600' },
  repairing: { label: '修复中', color: 'bg-yellow-600' },
  finalizing: { label: '收尾中', color: 'bg-blue-600' },
  completed: { label: '已完成', color: 'bg-green-600' },
  failed: { label: '失败', color: 'bg-red-600' },
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
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">任务历史</h1>
          <div className="flex gap-4">
            <Link href="/magazine" className="text-blue-400 hover:text-blue-300 text-sm">
              ← 杂志生成
            </Link>
            <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm">
              首页
            </Link>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-gray-500">加载中...</div>
        ) : tasks.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">暂无任务记录</p>
            <Link href="/" className="text-blue-400 hover:text-blue-300">
              上传文件开始
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {tasks.map(task => {
              const info = STATUS_MAP[task.status] || { label: task.status, color: 'bg-gray-600' }
              return (
                <div key={task.task_id} className="bg-gray-900 rounded-lg p-4 flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <span className={`${info.color} text-xs px-2 py-0.5 rounded-full text-white`}>
                        {info.label}
                      </span>
                      <span className="text-xs text-gray-500">
                        {task.created_at ? new Date(task.created_at).toLocaleString('zh-CN') : ''}
                      </span>
                    </div>
                    <div className="text-sm text-gray-300">
                      任务 {task.task_id.slice(0, 8)}
                      {task.fidelity_score != null && (
                        <span className="ml-3 text-gray-500">保真度: {(task.fidelity_score * 100).toFixed(1)}%</span>
                      )}
                    </div>
                    {task.message && task.status === 'failed' && (
                      <div className="text-xs text-red-400 mt-1">{task.message}</div>
                    )}
                    {task.progress > 0 && task.progress < 1 && (
                      <div className="mt-2 w-full bg-gray-800 rounded-full h-1">
                        <div className="bg-blue-500 h-1 rounded-full transition-all" style={{ width: `${task.progress * 100}%` }} />
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 ml-4">
                    {task.status === 'completed' && (
                      <button onClick={() => handleDownload(task.task_id, 'pdf')} className="text-xs bg-blue-600 hover:bg-blue-500 px-3 py-1.5 rounded-lg transition-colors">
                        下载
                      </button>
                    )}
                    {task.status === 'failed' && (
                      <Link href={`/magazine?task_id=${task.task_id}`} className="text-xs bg-yellow-700 hover:bg-yellow-600 px-3 py-1.5 rounded-lg transition-colors">
                        重试
                      </Link>
                    )}
                    <button onClick={() => handleDelete(task.task_id)} className="text-xs bg-gray-800 hover:bg-red-900 text-red-400 px-3 py-1.5 rounded-lg transition-colors">
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