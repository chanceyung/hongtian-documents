'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'
import ProgressBar from '@/components/ProgressBar'
import { magazineApi } from '@/lib/api'

export default function ImportPage() {
  const { magazineTask } = useAppStore()
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState<'pending' | 'processing' | 'completed' | 'failed'>('pending')

  useEffect(() => {
    if (!magazineTask) return

    const pollStatus = async () => {
      try {
        const response = await magazineApi.status(magazineTask.id)
        const taskData = response.data

        if (taskData.status === 'completed') {
          setStatus('completed')
          setProgress(100)
        } else if (taskData.status === 'failed') {
          setStatus('failed')
        } else {
          setStatus('processing')
          setProgress(taskData.progress || 0)
        }
      } catch (error) {
        console.error('Failed to fetch status:', error)
        setStatus('failed')
      }
    }

    const intervalId = setInterval(pollStatus, 2000)
    pollStatus()

    return () => clearInterval(intervalId)
  }, [magazineTask])

  if (!magazineTask) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">没有找到任务信息</p>
          <Link
            href="/"
            className="inline-block bg-brand-600 hover:bg-brand-700 text-white font-semibold py-2 px-6 rounded-lg"
          >
            返回首页
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 py-12">
      <div className="container mx-auto px-4">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-lg p-8">
            <h1 className="text-2xl font-bold text-brand-900 mb-6">
              正在解析文档
            </h1>

            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-brand-100 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="font-semibold text-gray-900">{magazineTask.fileName}</p>
                    <p className="text-sm text-gray-500">{magazineTask.fileSize}</p>
                  </div>
                </div>
                {status === 'completed' && (
                  <div className="text-green-600">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
                {status === 'failed' && (
                  <div className="text-red-600">
                    <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </div>
                )}
              </div>

              <ProgressBar
                progress={progress}
                label={status === 'completed' ? '解析完成' : '正在解析'}
                status={status}
              />

              <div className="text-sm text-gray-600">
                <p>任务 ID: {magazineTask.id}</p>
                {magazineTask.status && (
                  <p>当前阶段: {magazineTask.status}</p>
                )}
              </div>

              {status === 'completed' && (
                <div className="pt-4">
                  <Link
                    href="/magazine"
                    className="block w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3 px-6 rounded-lg text-center transition-colors"
                  >
                    继续生成杂志文档
                  </Link>
                </div>
              )}

              {status === 'failed' && (
                <div className="pt-4">
                  <Link
                    href="/"
                    className="block w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3 px-6 rounded-lg text-center transition-colors"
                  >
                    返回首页
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}