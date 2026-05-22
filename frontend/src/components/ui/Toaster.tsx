'use client'

import * as Toast from '@radix-ui/react-toast'
import { useEffect, useState } from 'react'

export interface ToastData {
  id: string
  title: string
  description?: string
  variant: 'success' | 'error' | 'info' | 'warning'
  duration?: number
}

let toastListeners: ((toasts: ToastData[]) => void)[] = []
let toasts: ToastData[] = []

export function toast(data: Omit<ToastData, 'id'>) {
  const newToast: ToastData = { ...data, id: crypto.randomUUID() }
  toasts = [...toasts, newToast]
  toastListeners.forEach(fn => fn([...toasts]))

  const duration = data.duration ?? 5000
  setTimeout(() => {
    toasts = toasts.filter(t => t.id !== newToast.id)
    toastListeners.forEach(fn => fn([...toasts]))
  }, duration)
}

export function Toaster() {
  const [items, setItems] = useState<ToastData[]>([])

  useEffect(() => {
    toastListeners.push(setItems)
    return () => {
      toastListeners = toastListeners.filter(fn => fn !== setItems)
    }
  }, [])

  const variantStyles: Record<string, string> = {
    success: 'border-green-600 bg-green-950',
    error: 'border-red-600 bg-red-950',
    info: 'border-blue-600 bg-blue-950',
    warning: 'border-yellow-600 bg-yellow-950',
  }

  return (
    <Toast.Provider swipeDirection="right">
      {items.map(t => (
        <Toast.Root
          key={t.id}
          className={`${variantStyles[t.variant]} border rounded-lg p-4 shadow-lg data-[state=open]:animate-slideIn data-[state=closed]:animate-slideOut relative`}
          duration={t.duration ?? 5000}
        >
          <Toast.Title className="text-sm font-medium text-gray-100">{t.title}</Toast.Title>
          {t.description && (
            <Toast.Description className="text-xs text-gray-400 mt-1">{t.description}</Toast.Description>
          )}
          <Toast.Close className="absolute top-2 right-2 text-gray-500 hover:text-gray-300 text-xs cursor-pointer">
            ✕
          </Toast.Close>
        </Toast.Root>
      ))}
      <Toast.Viewport className="fixed bottom-4 right-4 flex flex-col gap-2 w-80 z-50" />
    </Toast.Provider>
  )
}