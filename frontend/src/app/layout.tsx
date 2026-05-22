import './globals.css'
import type { Metadata } from 'next'
import { Toaster } from '@/components/ui/Toaster'
import { ApiInitializer } from '@/components/ApiInitializer'

export const metadata: Metadata = {
  title: '弘天文档 — 杂志级文档重构智能体',
  description: '将您的文档转化为杂志品质的 PDF 或 PPTX',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body>
        <ApiInitializer />
        {children}
        <Toaster />
      </body>
    </html>
  )
}