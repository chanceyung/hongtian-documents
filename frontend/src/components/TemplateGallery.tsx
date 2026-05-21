'use client'

import { useState } from 'react'
import { useAppStore } from '@/lib/store'

interface Template {
  id: string
  name: string
  description: string
  preview: string
}

const templates: Template[] = [
  {
    id: 'modern_tech',
    name: '现代科技风',
    description: '深色背景 + 科技蓝配色，适合技术展示和产品介绍',
    preview: '🌌',
  },
  {
    id: 'elegant_minimal',
    name: '优雅极简风',
    description: '浅色背景 + 极简设计，适合品牌介绍和企业年报',
    preview: '✨',
  },
  {
    id: 'business_professional',
    name: '商务专业风',
    description: '深蓝背景 + 金色点缀，适合金融报告和商务提案',
    preview: '💼',
  },
]

export default function TemplateGallery() {
  const { selectedTemplate, setSelectedTemplate } = useAppStore()
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {templates.map((tpl) => (
        <div
          key={tpl.id}
          className={`
            relative p-6 rounded-xl border-2 cursor-pointer transition-all duration-200
            ${selectedTemplate === tpl.id
              ? 'border-brand-500 bg-brand-50 shadow-lg'
              : 'border-gray-200 bg-white hover:border-brand-300 hover:shadow-md'
            }
          `}
          onClick={() => setSelectedTemplate(tpl.id)}
          onMouseEnter={() => setHoveredId(tpl.id)}
          onMouseLeave={() => setHoveredId(null)}
        >
          {selectedTemplate === tpl.id && (
            <div className="absolute top-3 right-3 w-6 h-6 bg-brand-500 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          )}

          <div className="text-4xl mb-3">{tpl.preview}</div>
          <h3 className="text-lg font-semibold text-gray-900 mb-1">{tpl.name}</h3>
          <p className="text-sm text-gray-500">{tpl.description}</p>

          {hoveredId === tpl.id && (
            <div className="mt-3 text-xs text-brand-600 font-medium">
              点击选择此模板
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
