'use client'

import { useState, useEffect, useCallback } from 'react'
import { useAppStore } from '@/lib/store'
import { apiKeyApi } from '@/lib/api'
import { toast } from '@/components/ui/Toaster'

export default function SettingsPage() {
  const { sessionId } = useAppStore()
  const [zhipuKey, setZhipuKey] = useState('')
  const [zhipuModel, setZhipuModel] = useState('glm-4-flash')
  const [visionKey, setVisionKey] = useState('')
  const [serpapiKey, setSerpapiKey] = useState('')
  const [fluxKey, setFluxKey] = useState('')
  const [fluxApiUrl, setFluxApiUrl] = useState('')

  const [configured, setConfigured] = useState(false)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const loadStatus = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const resp = await apiKeyApi.status(sessionId)
      const data = resp.data
      setConfigured(data.configured)
      if (data.zhipu_model) setZhipuModel(data.zhipu_model)
    } catch {
      setConfigured(false)
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => { loadStatus() }, [loadStatus])

  const handleSave = async () => {
    if (!zhipuKey && !visionKey && !serpapiKey && !fluxKey) {
      toast({ title: '保存失败', description: '请至少输入一个 API Key', variant: 'error' })
      return
    }
    setSaving(true)
    try {
      await apiKeyApi.save({
        sessionId,
        zhipuApiKey: zhipuKey || undefined,
        zhipuModel,
        zhipuVisionKey: visionKey || undefined,
        serpapiKey: serpapiKey || undefined,
        fluxKey: fluxKey || undefined,
        fluxApiUrl: fluxApiUrl || undefined,
      })
      toast({ title: '保存成功', description: 'API Key 已保存（24 小时有效）', variant: 'success' })
      setZhipuKey('')
      setVisionKey('')
      setSerpapiKey('')
      setFluxKey('')
      await loadStatus()
    } catch (e: any) {
      toast({ title: '保存失败', description: e.response?.data?.detail || '保存失败，请重试', variant: 'error' })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    try {
      const resp = await apiKeyApi.testZhipu(sessionId)
      const data = resp.data
      if (data.valid) {
        toast({ title: '测试成功', description: data.message, variant: 'success' })
      } else {
        toast({ title: '测试失败', description: data.message, variant: 'error' })
      }
    } catch (e: any) {
      toast({ title: '测试失败', description: e.response?.data?.detail || e.message, variant: 'error' })
    } finally {
      setTesting(false)
    }
  }

  const handleDelete = async () => {
    try {
      await apiKeyApi.delete(sessionId)
      setConfigured(false)
      toast({ title: '清除成功', description: '已清除所有 API Key', variant: 'success' })
    } catch {
      toast({ title: '清除失败', description: '清除 API Key 时出现错误', variant: 'error' })
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 p-8">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-2xl font-bold">设置</h1>
          <a href="/magazine" className="text-blue-400 hover:text-blue-300 text-sm">
            ← 返回杂志生成
          </a>
        </div>

        <div className={`rounded-lg p-4 mb-6 ${configured ? 'bg-green-900/30 border border-green-700' : 'bg-yellow-900/30 border border-yellow-700'}`}>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${configured ? 'bg-green-400' : 'bg-yellow-400'}`} />
            <span className="text-sm">
              {configured ? '智谱 API Key 已配置' : '未配置 API Key，请先配置'}
            </span>
          </div>
        </div>

        {message && (
          <div className={`rounded-lg p-4 mb-6 ${message.type === 'success' ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'}`}>
            <p className="text-sm">{message.text}</p>
          </div>
        )}

        <div className="bg-gray-900 rounded-lg p-6 mb-4">
          <h2 className="text-lg font-semibold mb-4">智谱 AI（必填）</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">API Key</label>
              <input
                type="password"
                value={zhipuKey}
                onChange={e => setZhipuKey(e.target.value)}
                placeholder={configured ? '已配置，输入新值可覆盖' : '请输入智谱 API Key'}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">模型</label>
              <select
                value={zhipuModel}
                onChange={e => setZhipuModel(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              >
                <option value="glm-4-flash">GLM-4-Flash（快速）</option>
                <option value="glm-4-air">GLM-4-Air（均衡）</option>
                <option value="glm-4-plus">GLM-4-Plus（精确）</option>
              </select>
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {saving ? '保存中...' : '保存'}
              </button>
              <button
                onClick={handleTest}
                disabled={testing || !configured}
                className="bg-gray-700 hover:bg-gray-600 disabled:bg-gray-800 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
              >
                {testing ? '测试中...' : '测试连接'}
              </button>
            </div>
          </div>
        </div>

        <details className="bg-gray-900 rounded-lg p-6 mb-4">
          <summary className="text-lg font-semibold cursor-pointer">可选配置</summary>
          <div className="space-y-4 mt-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Vision Key（图片理解）</label>
              <input
                type="password"
                value={visionKey}
                onChange={e => setVisionKey(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">SerpAPI Key（搜索）</label>
              <input
                type="password"
                value={serpapiKey}
                onChange={e => setSerpapiKey(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">FLUX Key（图片生成）</label>
              <input
                type="password"
                value={fluxKey}
                onChange={e => setFluxKey(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">FLUX API URL</label>
              <input
                type="text"
                value={fluxApiUrl}
                onChange={e => setFluxApiUrl(e.target.value)}
                placeholder="https://api.example.com/v1"
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>
        </details>

        <div className="bg-gray-900 rounded-lg p-6 border border-red-900/50">
          <h2 className="text-lg font-semibold text-red-400 mb-3">危险区域</h2>
          <button
            onClick={handleDelete}
            className="bg-red-900/50 hover:bg-red-800 text-red-300 px-4 py-2 rounded-lg text-sm font-medium transition-colors"
          >
            清除所有 API Key
          </button>
        </div>
      </div>
    </div>
  )
}