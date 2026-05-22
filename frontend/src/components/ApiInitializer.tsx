'use client'

import { useEffect } from 'react'
import { initApi } from '@/lib/api'

/**
 * 在 App 首次渲染时初始化 API 连接。
 * Electron 模式下会自动发现后端端口。
 */
export function ApiInitializer() {
  useEffect(() => {
    initApi().catch((err) => {
      console.error('[ApiInitializer] Failed to connect to backend:', err)
    })
  }, [])

  return null
}