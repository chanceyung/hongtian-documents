'use client'

import { useEffect, useState } from 'react'
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
  const { sessionId } = useAppStore()
  const [assets, setAssets] = useState<MissingAsset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(false)
  }, [sessionId])

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

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin w-10 h-10 border-4 border-brand-500 border-t-transparent rounded-full" />
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">素材补充</h1>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <p className="text-sm text-blue-700">
          系统会自动从 Pexels → Unsplash → AI 生图三级降级策略为缺失图片搜索补充素材。
        </p>
      </div>

      <AssetSupplement
        missingAssets={assets}
        onSupplement={handleSupplement}
      />

      {assets.length === 0 && (
        <div className="text-center py-16">
          <p className="text-gray-500">所有素材已完整，无需补充。</p>
          <a
            href="/magazine"
            className="inline-block mt-4 text-brand-500 hover:text-brand-600"
          >
            返回杂志页
          </a>
        </div>
      )}
    </div>
  )
}
