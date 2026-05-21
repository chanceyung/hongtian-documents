'use client'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center max-w-md">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">出错了</h2>
        <p className="text-gray-600 mb-8">
          应用发生了意外错误，请尝试刷新页面。
        </p>
        <button onClick={reset} className="btn-primary">
          重试
        </button>
      </div>
    </div>
  )
}
