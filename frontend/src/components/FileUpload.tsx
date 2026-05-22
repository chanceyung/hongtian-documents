'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { magazineApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'

interface FileUploadProps {
  onUploadSuccess: (taskData: any) => void
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const { sessionId } = useAppStore()
  const [isUploading, setIsUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0]
    if (!file) return

    setIsUploading(true)
    setUploadProgress(0)
    setError(null)

    try {
      const response = await magazineApi.upload(file, sessionId)
      setUploadProgress(100)

      const taskData = {
        id: response.data.task_id,
        fileName: file.name,
        fileSize: formatFileSize(file.size),
        status: 'pending',
        progress: 0,
        fidelityScore: null,
      }

      onUploadSuccess(taskData)
    } catch (err) {
      console.error('Upload failed:', err)
      setError('文件上传失败，请重试')
    } finally {
      setIsUploading(false)
    }
  }, [onUploadSuccess])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/markdown': ['.md'],
    },
    maxFiles: 1,
    disabled: isUploading,
  })

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <div className="space-y-5">
      <div
        {...getRootProps()}
        className={`
          relative rounded-xl p-10 text-center cursor-pointer transition-all duration-300
          border-2 border-dashed
          ${isDragActive
            ? 'border-accent/60 bg-accent/[0.06]'
            : 'border-white/[0.1] hover:border-white/[0.2] hover:bg-white/[0.02]'
          }
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="space-y-4">
          <div className={`mx-auto w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 ${
            isDragActive ? 'bg-accent/20' : 'bg-white/[0.05]'
          }`}>
            {isUploading ? (
              <div className="relative">
                <div className="animate-spin rounded-full h-7 w-7 border-2 border-accent/30 border-t-accent" />
              </div>
            ) : (
              <svg className={`w-6 h-6 transition-colors duration-300 ${isDragActive ? 'text-accent-light' : 'text-white/40'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            )}
          </div>

          {isUploading ? (
            <div>
              <p className="text-base font-medium text-white/80">正在上传...</p>
              <div className="mt-3 w-48 mx-auto h-1 rounded-full bg-white/[0.06] overflow-hidden">
                <div className="h-full rounded-full bg-gradient-to-r from-accent-dark to-accent-light transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          ) : (
            <div>
              <p className="text-base font-medium text-white/70">
                {isDragActive ? '释放文件以上传' : '拖拽文件到这里，或点击选择'}
              </p>
              <p className="text-sm text-white/30 mt-2">
                支持 PPTX、PDF、DOCX、XLSX、MD 格式
              </p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-500/[0.08] border border-red-500/20 rounded-xl p-4">
          <svg className="w-4 h-4 text-red-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-red-300 text-sm">{error}</p>
        </div>
      )}

      <p className="text-center text-xs text-white/20">
        文件将立即开始解析，无需等待
      </p>
    </div>
  )
}
