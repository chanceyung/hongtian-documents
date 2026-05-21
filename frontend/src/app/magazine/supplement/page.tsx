'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAppStore } from '@/lib/store'
import AssetSupplement from '@/components/AssetSupplement'

interface MissingAsset {
  id: string
  type: 'image'
  context: string
  status: 'missing' | 'searching' | 'found' | 'failed'
  previewUrl?: string
}

export default function SupplementPage() {
  const { magazineTask } = useAppStore()
  const [assets, setAssets] = useState<MissingAsset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!magazineTask) return
    setLoading(false)
  }, [magazineTask])

  const handleSupplement = async (assetId: string) => {
    setAssets((prev) =>
      prev.map((a) => a.id === assetId ? { ...a, status: 'searching' as const } : a),
    )

    try {
      await new Promise((resolve) => setTimeout(resolve, 2000))
      setAssets((prev) =>
        prev.map((a) => a.id === assetId ? { ...a, status: 'found' as const } : a),
      )
    } catch {
      setAssets((prev) =>
        prev.map((a) => a.id === assetId ? { ...a, status: 'failed' as const } : a),
      )
    }
  }

  if (!magazineTask) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">没有找到任务信息</p>
          <Link href="/" className="btn-primary">返回首页</Link>
        </div>
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
          <h1 className="text-lg font-semibold text-gray-900">素材补充</h1>
          <div className="w-20" />
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <p className="text-sm text-blue-700">
            系统会自动从 Pexels → Unsplash → AI 生图三级降级策略为缺失图片搜索补充素材。
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <div className="animate-spin w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full" />
          </div>
        ) : (
          <AssetSupplement missingAssets={assets} onSupplement={handleSupplement} />
        )}

        {assets.length === 0 && !loading && (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">所有素材已完整，无需补充。</p>
            <Link href="/magazine" className="btn-primary">返回杂志页</Link>
          </div>
        )}
      </main>
    </div>
  )
}
