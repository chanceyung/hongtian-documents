<p align="center">
  <img src="logo/Black.png" alt="弘天 AI" width="120" />
</p>

<h1 align="center">弘天文档 — 杂志级文档重构智能体</h1>

<p align="center">
  <strong>将客户文档转化为杂志品质的 PDF / PPTX</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/版本-V4-blue" alt="V4" />
  <img src="https://img.shields.io/badge/Python-≥3.11-green" alt="Python" />
  <img src="https://img.shields.io/badge/TypeScript-strict-blue" alt="TypeScript" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License" />
</p>

---

## 项目简介

弘天文档是一个智能文档重构系统，接受多种格式的客户文档（PPTX、PDF、Word、Excel、Markdown），提取全部内容并保持图文对应关系，然后重新排版生成杂志级的 PDF 或 PPTX 文件。

### 核心特性

- **内容 100% 保真** — 基于 PPTAgent 的 edit-based 方法，只替换不重写，确保原文意思完整保留
- **多格式支持** — PPTX / PDF / DOCX / XLSX / Markdown 五种输入格式
- **图文关联** — 三重策略（空间距离 + 结构关键词 + 语义分析）确保图文对应
- **素材补充** — 自动从免费图库搜索或 AI 生图补充缺失素材
- **双轨渲染** — PDF（Playwright + WeasyPrint 混合引擎）/ PPTX（PPT Master SVG→DrawingML）
- **四层保真校验** — 指纹完整性 → 图文关联 → 语义保真 → 人工确认
- **零 GPU 部署** — 所有 AI 处理通过 GLM-5 API 完成，4 个 Docker 容器即可运行

---

## 系统架构

```
用户上传文档
    │
    ▼
┌─ Presenton 前端 (Next.js) ──────────────────────────────┐
│  多格式导入 / 模板选择 / 实时预览 / 保真报告 / 素材补充  │
└─────────────────────┬───────────────────────────────────┘
                      │ API
                      ▼
┌─ FastAPI 后端 ──────────────────────────────────────────┐
│                                                          │
│  Parser Agent ─→ Analyzer Agent ─→ Designer Agent        │
│       │                │                   │              │
│       ▼                ▼                   ▼              │
│  UnifiedDocument   内容聚类+模式提取   编辑动作(只替换)   │
│                                                          │
│  ─→ Supplement Agent ─→ Renderer Agent ─→ Fidelity Agent │
│        素材搜索/AI生图    PDF/PPTX双轨渲染   四层保真校验 │
│                                                          │
│  LangGraph 状态图编排 · GLM-5 API · Redis 缓存          │
└──────────────────────────────────────────────────────────┘
```

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 前端 | Next.js + TypeScript + Zustand | Presenton UI 框架 |
| 后端 | FastAPI + Python 3.11+ | API 服务 |
| AI | GLM-5 API (OpenAI SDK) | 所有 AI 处理 |
| 工作流 | LangGraph | 多智能体编排 |
| PDF 渲染 | Playwright + WeasyPrint | 混合引擎 |
| PPTX 生成 | PPT Master (SVG→DrawingML) | 高保真转换 |
| PDF 解析 | Docling + PyMuPDF | 双策略解析 |
| 缓存 | Redis | API Key + 任务状态 |
| 部署 | Docker Compose (4 服务) | 一键部署 |

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repo-url> 弘天文档
cd 弘天文档

# 复制环境变量
cp .env.example .env
# 编辑 .env，填入 GLM_API_KEY（必填）
```

### 2. 启动服务

```bash
# 使用 V4 精简配置
docker compose -f docker-compose-v4.yml up -d

# 访问
# 前端: http://localhost:3000
# 后端 API: http://localhost:8000/docs
```

### 3. 本地开发

```bash
# 后端
cd backend
pip install -r requirements-v4.txt
playwright install chromium
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

---

## 项目文档

| 文档 | 说明 |
|------|------|
| [CLAUDE.md](CLAUDE.md) | 开发规则（必须遵守） |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | 文件结构与核心流程 |
| [INTEGRATION_GUIDE_V4.md](INTEGRATION_GUIDE_V4.md) | 集成指南（架构 + 接口 + 代码骨架） |
| [IMPLEMENTATION_COMPLETE.md](IMPLEMENTATION_COMPLETE.md) | 完整实现代码 |
| [ARCHITECTURE_V4_OPENSOURCE.md](ARCHITECTURE_V4_OPENSOURCE.md) | 开源选型论证 |

---

## 开源项目致谢

本项目集成并改进了以下优秀开源项目：

- **[Presenton](https://github.com/onwidget/presenton)** — Next.js PPT 制作框架（UI 壳）
- **[PPTAgent](https://github.com/voidpatrick/PPTAgent)** — 中科院 edit-based PPT 重构思想
- **[PPT Master](https://github.com/lirenni/PPT-Master)** — SVG→DrawingML→PPTX 高保真转换

---

## 许可证

MIT License

---

<p align="center">
  <img src="logo/White.png" alt="弘天 AI" width="60" />
  <br/>
  <sub>弘天 AI · 让文档更有力量</sub>
</p>
