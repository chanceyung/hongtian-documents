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
    <div className="page-container">
      <div className="max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-white mb-8">设置</h1>

        <div className={`glass-card p-4 mb-6 flex items-center gap-3 ${configured ? '' : ''}`}>
          <div className={`w-2 h-2 rounded-full animate-pulse-glow ${configured ? 'bg-emerald-400' : 'bg-amber-400'}`} />
          <span className="text-sm text-white/60">
            {configured ? '智谱 API Key 已配置' : '未配置 API Key，请先配置'}
          </span>
        </div>

        {message && (
          <div className={`glass-card p-4 mb-6 ${message.type === 'success' ? 'border-emerald-500/30' : 'border-red-500/30'}`}>
            <p className="text-sm text-white/70">{message.text}</p>
          </div>
        )}

        <div className="glass-card p-6 mb-4">
          <h2 className="section-title">智谱 AI（必填）</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-white/40 mb-1.5">API Key</label>
              <input
                type="password"
                value={zhipuKey}
                onChange={e => setZhipuKey(e.target.value)}
                placeholder={configured ? '已配置，输入新值可覆盖' : '请输入智谱 API Key'}
                className="input-dark"
              />
            </div>
            <div>
              <label className="block text-sm text-white/40 mb-1.5">模型</label>
              <select
                value={zhipuModel}
                onChange={e => setZhipuModel(e.target.value)}
                className="input-dark appearance-none"
              >
                <option value="glm-4-flash">GLM-4-Flash（快速）</option>
                <option value="glm-4-air">GLM-4-Air（均衡）</option>
                <option value="glm-4-plus">GLM-4-Plus（精确）</option>
              </select>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary"
              >
                {saving ? '保存中...' : '保存'}
              </button>
              <button
                onClick={handleTest}
                disabled={testing || !configured}
                className="btn-secondary"
              >
                {testing ? '测试中...' : '测试连接'}
              </button>
            </div>
          </div>
        </div>

        <details className="glass-card p-6 mb-4 group">
          <summary className="text-white font-semibold cursor-pointer flex items-center gap-2">
            <svg className="w-4 h-4 text-white/30 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
            可选配置
          </summary>
          <div className="space-y-4 mt-5 pl-6">
            <div>
              <label className="block text-sm text-white/40 mb-1.5">Vision Key（图片理解）</label>
              <input type="password" value={visionKey} onChange={e => setVisionKey(e.target.value)} className="input-dark" />
            </div>
            <div>
              <label className="block text-sm text-white/40 mb-1.5">SerpAPI Key（搜索）</label>
              <input type="password" value={serpapiKey} onChange={e => setSerpapiKey(e.target.value)} className="input-dark" />
            </div>
            <div>
              <label className="block text-sm text-white/40 mb-1.5">FLUX Key（图片生成）</label>
              <input type="password" value={fluxKey} onChange={e => setFluxKey(e.target.value)} className="input-dark" />
            </div>
            <div>
              <label className="block text-sm text-white/40 mb-1.5">FLUX API URL</label>
              <input type="text" value={fluxApiUrl} onChange={e => setFluxApiUrl(e.target.value)} placeholder="https://api.example.com/v1" className="input-dark" />
            </div>
          </div>
        </details>

        <div className="glass-card p-6 border-red-500/20">
          <h2 className="text-red-400 font-semibold mb-3">危险区域</h2>
          <button
            onClick={handleDelete}
            className="px-4 py-2 rounded-xl text-sm font-medium bg-red-500/10 border border-red-500/20 text-red-300 hover:bg-red-500/20 transition-colors"
          >
            清除所有 API Key
          </button>
        </div>
      </div>
    </div>
  )
}
