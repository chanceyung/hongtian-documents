import './globals.css'
import type { Metadata } from 'next'
import Link from 'next/link'
import { Toaster } from '@/components/ui/Toaster'
import { ApiInitializer } from '@/components/ApiInitializer'

export const metadata: Metadata = {
  title: '弘天文档 — 杂志级文档重构智能体',
  description: '将您的文档转化为杂志品质的 PDF 或 PPTX',
}

function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 flex items-center justify-between px-6 bg-surface/70 backdrop-blur-xl border-b border-white/[0.06]">
      <Link href="/" className="flex items-center gap-2.5 group">
        <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-brand-500 flex items-center justify-center text-white text-xs font-bold">
          弘
        </div>
        <span className="text-white font-semibold text-sm group-hover:text-accent-light transition-colors">
          弘天文档
        </span>
      </Link>
      <div className="flex items-center gap-6">
        <Link href="/" className="nav-link">首页</Link>
        <Link href="/history" className="nav-link">历史</Link>
        <Link href="/settings" className="nav-link">设置</Link>
      </div>
    </nav>
  )
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
        <Navbar />
        <main className="pt-14 min-h-screen">
          {children}
        </main>
        <Toaster />
      </body>
    </html>
  )
}
