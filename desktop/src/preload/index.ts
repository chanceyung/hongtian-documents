/**
 * Preload 脚本 — 安全的 IPC 桥接
 */
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendPort: () => ipcRenderer.invoke('get-backend-port'),
  platform: process.platform,
  openFile: (filters: any) => ipcRenderer.invoke('dialog:openFile', filters),
  getVersion: () => ipcRenderer.invoke('app:getVersion'),
  minimize: () => ipcRenderer.invoke('window:minimize'),
  maximize: () => ipcRenderer.invoke('window:maximize'),
  close: () => ipcRenderer.invoke('window:close'),
})

// 菜单事件转发
ipcRenderer.on('menu:open-file', () => {
  globalThis.dispatchEvent(new CustomEvent('menu:open-file'))
})