'use client'

import { useState } from 'react'

interface DocumentPreviewProps {
  fileUrl: string
  fileType: 'pdf' | 'pptx'
  fileName?: string
}

export default function DocumentPreview({ fileUrl, fileType, fileName }: DocumentPreviewProps) {
  const [loading, setLoading] = useState(true)

  if (fileType === 'pptx') {
    return (
      <div className="border border-gray-200 rounded-lg p-8 text-center">
        <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
            d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
        </svg>
        <p className="text-gray-600 mb-2">PPTX 文件预览</p>
        <p className="text-sm text-gray-400">{fileName || 'magazine.pptx'}</p>
        <a
          href={fileUrl}
          download={fileName || 'magazine.pptx'}
          className="inline-block mt-4 px-4 py-2 bg-brand-500 text-white rounded-lg hover:bg-brand-600 transition-colors"
        >
          下载 PPTX
        </a>
      </div>
    )
  }

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {loading && (
        <div className="flex items-center justify-center h-96">
          <div className="animate-spin w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full" />
        </div>
      )}
      <iframe
        src={fileUrl}
        className="w-full h-[600px]"
        onLoad={() => setLoading(false)}
        title="文档预览"
      />
    </div>
  )
}
