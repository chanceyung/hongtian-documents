/**
 * Preload 脚本 — 安全的 IPC 桥接
 */
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  // 获取后端端口
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),

  // 平台信息
  platform: process.platform,

  // 文件对话框
  openFile: (filters: any) => ipcRenderer.invoke('dialog:openFile', filters),

  // 版本
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
})

// 菜单事件转发
ipcRenderer.on('menu:open-file', () => {
  window.dispatchEvent(new CustomEvent('menu:open-file'))
})