'use client'

interface FidelityReportProps {
  score: number
  passed: boolean
  l1Score: number
  l2Score: number
  l3Score: number
  issues: Array<{
    level: string
    category: string
    description: string
    element_id?: string
    original?: string
  }>
}

export default function FidelityReport({
  score, passed, l1Score, l2Score, l3Score, issues,
}: FidelityReportProps) {
  const criticalIssues = issues.filter((i) => i.level === 'critical')
  const warnings = issues.filter((i) => i.level === 'warning')

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-6">
        <ScoreGauge score={score} passed={passed} />
        <div className="flex-1 space-y-2">
          <CheckItem label="L1 指纹完整性" score={l1Score} weight="40%" />
          <CheckItem label="L2 图文关联" score={l2Score} weight="30%" />
          <CheckItem label="L3 语义保真" score={l3Score} weight="30%" />
        </div>
      </div>

      {criticalIssues.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h4 className="text-red-800 font-semibold mb-2">
            严重问题 ({criticalIssues.length})
          </h4>
          {criticalIssues.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} variant="critical" />
          ))}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <h4 className="text-yellow-800 font-semibold mb-2">
            警告 ({warnings.length})
          </h4>
          {warnings.map((issue, idx) => (
            <IssueCard key={idx} issue={issue} variant="warning" />
          ))}
        </div>
      )}

      {passed && issues.length === 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <p className="text-green-700 font-medium">所有保真校验通过</p>
        </div>
      )}
    </div>
  )
}

function ScoreGauge({ score, passed }: { score: number; passed: boolean }) {
  const percentage = Math.round(score * 100)
  const color = passed ? 'text-green-600' : 'text-red-600'
  const ringColor = passed ? 'stroke-green-500' : 'stroke-red-500'

  return (
    <div className="relative w-32 h-32 flex items-center justify-center">
      <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r="52" fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle
          cx="60" cy="60" r="52" fill="none"
          className={ringColor}
          strokeWidth="8"
          strokeDasharray={`${percentage * 3.27} 327`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-2xl font-bold ${color}`}>{percentage}%</span>
        <span className="text-xs text-gray-500">保真度</span>
      </div>
    </div>
  )
}

function CheckItem({ label, score, weight }: { label: string; score: number; weight: string }) {
  const percentage = Math.round(score * 100)
  const color = score >= 0.95 ? 'bg-green-500' : score >= 0.8 ? 'bg-yellow-500' : 'bg-red-500'

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 w-28 shrink-0">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${percentage}%` }} />
      </div>
      <span className="text-sm font-mono text-gray-700 w-12 text-right">{percentage}%</span>
      <span className="text-xs text-gray-400 w-10">{weight}</span>
    </div>
  )
}

function IssueCard({ issue, variant }: { issue: FidelityReportProps['issues'][0]; variant: 'critical' | 'warning' }) {
  const bgColor = variant === 'critical' ? 'bg-red-100' : 'bg-yellow-100'
  const textColor = variant === 'critical' ? 'text-red-700' : 'text-yellow-700'

  return (
    <div className={`${bgColor} rounded p-3 mb-2`}>
      <div className="flex items-center gap-2 mb-1">
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${bgColor} ${textColor}`}>
          {issue.category}
        </span>
      </div>
      <p className={`text-sm ${textColor}`}>{issue.description}</p>
      {issue.original && (
        <p className="text-xs text-gray-500 mt-1 truncate">原文: {issue.original}</p>
      )}
    </div>
  )
}
