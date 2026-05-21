'use client'

import { useState } from 'react'
import Link from 'next/link'
import FileUpload from '@/components/FileUpload'
import { useAppStore } from '@/lib/store'

export default function Home() {
  const [showResults, setShowResults] = useState(false)
  const { magazineTask, setMagazineTask } = useAppStore()

  const handleUploadSuccess = (taskData: any) => {
    setMagazineTask(taskData)
    setShowResults(true)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-800 via-brand-700 to-brand-900">
      <div className="container mx-auto px-4 py-12">
        <div className="max-w-4xl mx-auto text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4">
            弘天文档
          </h1>
          <p className="text-xl text-brand-100 mb-8">
            杂志级文档重构智能体
          </p>
          <p className="text-brand-200 mb-8">
            将 PPTX、PDF、Word、Excel、Markdown 文档转化为杂志品质的 PDF 或 PPTX
          </p>
        </div>

        {!showResults ? (
          <div className="max-w-2xl mx-auto">
            <FileUpload onUploadSuccess={handleUploadSuccess} />
          </div>
        ) : (
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
              <h2 className="text-xl font-bold text-brand-900 mb-4">
                解析完成
              </h2>
              {magazineTask && (
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">状态</span>
                    <span className="text-green-600 font-semibold">
                      {magazineTask.status}
                    </span>
                  </div>
                  {magazineTask.fidelityScore && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600">内容保真度</span>
                      <span className="text-brand-600 font-semibold">
                        {(magazineTask.fidelityScore * 100).toFixed(1)}%
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <Link
              href="/magazine"
              className="block w-full bg-brand-600 hover:bg-brand-700 text-white font-semibold py-3 px-6 rounded-lg text-center transition-colors"
            >
              继续生成杂志文档
            </Link>

            <button
              onClick={() => setShowResults(false)}
              className="block w-full mt-4 text-brand-200 hover:text-white font-medium transition-colors"
            >
              上传新文件
            </button>
          </div>
        )}
      </div>
    </div>
  )
}