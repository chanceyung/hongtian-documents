import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-brand-800 mb-4">404</h1>
        <p className="text-xl text-gray-600 mb-8">页面不存在</p>
        <Link
          href="/"
          className="btn-primary"
        >
          返回首页
        </Link>
      </div>
    </div>
  )
}
