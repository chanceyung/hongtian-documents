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
    <div className="space-y-6">
      <div
        {...getRootProps()}
        className={`
          border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-all
          ${isDragActive ? 'border-brand-500 bg-brand-50' : 'border-brand-300 hover:border-brand-500'}
          ${isUploading ? 'pointer-events-none opacity-60' : ''}
        `}
      >
        <input {...getInputProps()} />

        <div className="space-y-4">
          <div className="mx-auto w-16 h-16 bg-brand-100 rounded-full flex items-center justify-center">
            {isUploading ? (
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600"></div>
            ) : (
              <svg className="w-8 h-8 text-brand-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            )}
          </div>

          {isUploading ? (
            <div>
              <p className="text-lg font-medium text-gray-900">正在上传...</p>
              <p className="text-gray-600">{uploadProgress}%</p>
            </div>
          ) : (
            <div>
              <p className="text-lg font-medium text-gray-900">
                {isDragActive ? '释放文件以上传' : '拖拽文件到这里，或点击选择文件'}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                支持 PPTX、PDF、DOCX、XLSX、MD 格式
              </p>
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-red-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      <div className="text-center text-sm text-gray-500">
        <p>文件将立即开始解析，无需等待</p>
      </div>
    </div>
  )
}