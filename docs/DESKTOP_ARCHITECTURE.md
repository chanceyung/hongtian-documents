# 弘天文档 — 桌面版架构说明

## 架构概览

```
┌─────────────────────────────────────────┐
│           Electron Shell                │
│  ┌────────────────────────────────────┐ │
│  │         Chromium WebView           │ │
│  │   ┌────────────────────────────┐   │ │
│  │   │   Next.js Frontend         │   │ │
│  │   │   (standalone output)      │   │ │
│  │   └────────────────────────────┘   │ │
│  └────────────────────────────────────┘ │
│                                         │
│  子进程: Python Backend (uvicorn)       │
│  ┌────────────────────────────────────┐ │
│  │  FastAPI + SQLite KV + AI Agents   │ │
│  │  (PyInstaller 打包)                │ │
│  └────────────────────────────────────┘ │
│                                         │
│  数据目录: %APPDATA%/hongtian-docs/     │
└─────────────────────────────────────────┘
```

## 依赖简化策略

| 组件 | 服务器版 | 桌面版替代 | 节省 |
|------|---------|-----------|------|
| Redis | redis:7-alpine | SQLite KV Store | ~256MB |
| Docling | docling + torch | PyMuPDF (已有) | ~800MB |
| Playwright | Chromium 渲染 | WeasyPrint 统一 | ~400MB |
| LangGraph | langgraph | 直接函数调用 | ~50MB |
| torch/transformers | AI 模型 | 不需要 | ~500MB |

**预计打包体积: ~200-350MB** (vs Docker 镜像 ~2.5GB)

## 开发

```bash
# 桌面开发模式（无需 Redis）
scripts\dev-desktop.bat

# 或手动启动:
# 1. 后端
cd backend
set DESKTOP_MODE=true
venv\Scripts\python -m uvicorn app.main:app --port 8000

# 2. 前端
cd frontend
npm run dev
```

## 构建

```bash
# Windows 一键构建
scripts\build-desktop.bat

# 或分步:
# 1. 构建前端
cd frontend && npm run build

# 2. 打包后端
cd backend
pip install -r requirements-desktop.txt
pyinstaller ../desktop/hongtian-backend.spec

# 3. 构建 Electron
cd desktop
npm run build:win
```

## 文件结构

```
desktop/
├── package.json          # Electron 主配置 + electron-builder
├── tsconfig.main.json    # 主进程 TS 配置
├── hongtian-backend.spec # PyInstaller 打包配置 (在 desktop/)
├── src/
│   ├── main/
│   │   ├── index.ts      # Electron 主进程
│   │   └── port-utils.ts # 端口查找
│   └── preload/
│       └── index.ts      # 安全 IPC 桥接
├── resources/
│   └── icon.png          # 应用图标
├── dist/                 # 编译输出
└── release/              # 安装包输出

backend/
├── requirements-desktop.txt  # 桌面版精简依赖
├── desktop_main.py           # 桌面版启动入口
├── app/core/
│   ├── kv_store.py           # SQLite KV 存储
│   └── redis.py              # Redis 兼容层（自动切换）
```

## 环境变量

| 变量 | 桌面版默认 | 说明 |
|------|-----------|------|
| DESKTOP_MODE | true | 使用 SQLite 替代 Redis |
| PORT | 8000 | 后端端口（自动检测） |
| DATABASE_URL | SQLite (userData) | 任务数据库 |
| CORS_ORIGINS | localhost:PORT | 跨域配置 |

## 仍需联网的服务

- **GLM-5 API** — 文档分析/设计/保真校验（必须）
- **Pexels/Unsplash** — 素材补充（可选）
- **Replicate** — AI 生图（可选）

核心解析→渲染→导出流程完全本地运行。