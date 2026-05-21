'use client'

import { useState } from 'react'

interface MissingAsset {
  id: string
  type: 'image'
  context: string
  status: 'missing' | 'searching' | 'found' | 'failed'
  previewUrl?: string
}

interface AssetSupplementProps {
  missingAssets: MissingAsset[]
  onSupplement: (assetId: string) => Promise<void>
}

export default function AssetSupplement({ missingAssets, onSupplement }: AssetSupplementProps) {
  const [processingId, setProcessingId] = useState<string | null>(null)

  const handleSupplement = async (assetId: string) => {
    setProcessingId(assetId)
    try {
      await onSupplement(assetId)
    } finally {
      setProcessingId(null)
    }
  }

  const handleSupplementAll = async () => {
    const missing = missingAssets.filter((a) => a.status === 'missing')
    for (const asset of missing) {
      await handleSupplement(asset.id)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900">
          缺失素材 ({missingAssets.length})
        </h3>
        <button
          onClick={handleSupplementAll}
          disabled={processingId !== null}
          className="px-4 py-2 text-sm bg-brand-500 text-white rounded-lg hover:bg-brand-600 disabled:opacity-50 transition-colors"
        >
          一键补充全部
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {missingAssets.map((asset) => (
          <div
            key={asset.id}
            className="border border-gray-200 rounded-lg p-4 flex gap-4"
          >
            <div className="w-24 h-24 bg-gray-100 rounded flex items-center justify-center shrink-0 overflow-hidden">
              {asset.previewUrl ? (
                <img src={asset.previewUrl} alt="" className="w-full h-full object-cover" />
              ) : (
                <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14" />
                </svg>
              )}
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{asset.id}</p>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">{asset.context}</p>

              <div className="mt-2 flex items-center gap-2">
                <StatusBadge status={asset.status} />
                {asset.status === 'missing' && (
                  <button
                    onClick={() => handleSupplement(asset.id)}
                    disabled={processingId !== null}
                    className="text-xs text-brand-500 hover:text-brand-600 disabled:opacity-50"
                  >
                    {processingId === asset.id ? '搜索中...' : '补充'}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {missingAssets.length === 0 && (
        <div className="text-center py-8 text-gray-400">
          所有素材完整，无需补充
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: MissingAsset['status'] }) {
  const styles = {
    missing: 'bg-gray-100 text-gray-600',
    searching: 'bg-blue-100 text-blue-700',
    found: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
  }
  const labels = {
    missing: '缺失',
    searching: '搜索中',
    found: '已补充',
    failed: '失败',
  }

  return (
    <span className={`text-xs px-2 py-0.5 rounded ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}
