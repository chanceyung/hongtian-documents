interface ProgressBarProps {
  progress: number
  label: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
}

export default function ProgressBar({ progress, label, status }: ProgressBarProps) {
  const getStatusColor = () => {
    switch (status) {
      case 'processing':
        return 'bg-brand-500'
      case 'completed':
        return 'bg-green-500'
      case 'failed':
        return 'bg-red-500'
      default:
        return 'bg-gray-300'
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm font-medium text-gray-700">{label}</span>
        <span className="text-sm font-semibold text-gray-900">{progress}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div
          className={`${getStatusColor()} h-full transition-all duration-300 ease-out`}
          style={{ width: `${progress}%` }}
        />
      </div>
      {status === 'processing' && (
        <div className="flex items-center justify-center space-x-2">
          <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-2 h-2 bg-brand-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      )}
    </div>
  )
}