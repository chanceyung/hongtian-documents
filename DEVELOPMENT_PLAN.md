# 弘天文档 V4 — 完整开发计划

> 本文档是项目的开发路线图，分为三个阶段执行。
> 详细计划文件: `C:\Users\chanc\.claude\plans\magical-strolling-squirrel.md`

---

## 项目现状

| 类别 | 状态 |
|------|------|
| V1 后端代码 | ~1,043 行可用（parser.py, zhipu_client.py, redis.py, API Key 管理） |
| V4 架构文档 | 完整（集成指南 + 实现代码 + 选型论证） |
| 开发规则 | 完整（CLAUDE.md, CONTRIBUTING.md） |
| Docker 配置 | V4 可用（4 服务） |
| 前端 | 仅骨架（4 文件，无页面无组件） |
| 模板 | 仅有 config.json，无 HTML/CSS/SVG 文件 |

---

## 阶段一：初始开发目标 — MVP 端到端验证（4 周）

**目标**: PPTX 单格式跑通完整流程，验证架构可行。

### 第 1 周：基础设施 + 数据模型

| 任务 | 文件 | 说明 |
|------|------|------|
| Git 初始化 | `.gitignore` | Python/Node/环境变量/数据目录 |
| 配置更新 | `backend/app/core/config.py` | 移除 V1 配置，增加 V4 字段 |
| 主入口更新 | `backend/app/main.py` | 注册 V4 路由 + 健康检查 |
| 统一文档模型 | `backend/app/models/unified_document.py` | BoundingBox, TextElement, ImageElement, TableElement, ContentAssetLink, ContentFingerprint, UnifiedDocument |
| 编辑动作模型 | `backend/app/models/edit_actions.py` | EditAction, PageEditPlan, MagazineEditPlan |
| 设计规格模型 | `backend/app/models/design_spec.py` | ColorScheme, TypographySpec, LayoutSpec, DesignSpec |
| 自定义异常 | `backend/app/exceptions.py` | 异常层级定义 |

### 第 1-2 周：PPTX 解析器

| 任务 | 文件 | 说明 |
|------|------|------|
| 解析器基类 | `backend/app/parsers/base_parser.py` | ParserProtocol 抽象基类 |
| 解析器工厂 | `backend/app/parsers/parser_factory.py` | 按格式分发 |
| PPTX 解析器 | `backend/app/parsers/pptx_parser.py` | 重构 V1 parser.py，输出 UnifiedDocument |

### 第 2-3 周：六智能体 + LangGraph

| 任务 | 文件 | 说明 |
|------|------|------|
| Parser Agent | `backend/app/agents/parser_agent.py` | 格式路由 + 错误重试 |
| Analyzer Agent | `backend/app/agents/analyzer_agent.py` | GLM-5 内容聚类 + 模式提取 |
| Designer Agent | `backend/app/agents/designer_agent.py` | **replace-only** 编辑动作生成 |
| Renderer Agent | `backend/app/agents/renderer_agent.py` | MVP: 仅 PPTX 输出 |
| Fidelity Agent | `backend/app/agents/fidelity_agent.py` | MVP: L1 指纹 + L2 图文 |
| Supplement Agent | `backend/app/agents/supplement_agent.py` | MVP: 占位符 |
| SVG→DrawingML | `backend/app/exporters/ppt_master/svg_to_pptx.py` | PPT Master 转换 |
| SVG 后处理 | `backend/app/exporters/ppt_master/finalize_svg.py` | 移除禁用元素 |
| 工作流状态 | `backend/app/workflow/state.py` | MagazineState 定义 |
| 工作流引擎 | `backend/app/workflow/magazine_pipeline.py` | LangGraph StateGraph 编排 |

### 第 3 周：PPTX 模板

| 任务 | 文件 | 说明 |
|------|------|------|
| 空白模板 | `templates/pptx/modern_tech/template.pptx` | 16:9 空白 |
| 封面 SVG | `pages/cover.svg` | 含 White.png Logo |
| 文字页 SVG | `pages/content_text.svg` | 纯文字布局 |
| 图文页 SVG | `pages/content_image_text.svg` | 图文混排布局 |
| 数据卡片 SVG | `pages/data_card.svg` | 数据展示布局 |

### 第 3-4 周：前端基础

| 任务 | 文件 | 说明 |
|------|------|------|
| TS 配置 | `frontend/tsconfig.json` | strict: true |
| Next.js 配置 | `frontend/next.config.ts` | — |
| Tailwind 配置 | `frontend/tailwind.config.ts` | 自定义主题 |
| 根布局 | `frontend/src/app/layout.tsx` | Logo + 导航 |
| 首页 | `frontend/src/app/page.tsx` | 文件上传入口 |
| 导入页 | `frontend/src/app/import/page.tsx` | 上传 → 解析进度 |
| 杂志页 | `frontend/src/app/magazine/page.tsx` | 模板选择 → 生成 → 下载 |
| 文件上传组件 | `frontend/src/components/FileUpload.tsx` | 拖拽上传 |
| 进度条组件 | `frontend/src/components/ProgressBar.tsx` | 各阶段进度 |
| API 增强 | `frontend/src/lib/api.ts` | 杂志 API 方法 |
| 状态增强 | `frontend/src/lib/store.ts` | 杂志状态字段 |

### 第 4 周：API 路由

| 任务 | 文件 | 说明 |
|------|------|------|
| V4 API | `backend/app/api/v1/magazine.py` | 5 个端点：upload/status/generate/fidelity/download |

### 阶段一验收标准

用户完整流程：访问首页 → 输入 API Key → 上传 PPTX → 看解析进度 → 选模板 → 生成 → 下载 → 用 PowerPoint 打开验证内容完整。

---

## 阶段二：迭代开发目标 — 全格式 + 全功能（5 周）

**目标**: 5 种输入格式、完善智能体、双轨渲染、3 套模板。

### 第 5-6 周：剩余格式解析器

| 文件 | 说明 |
|------|------|
| `parsers/pdf_parser.py` | Docling 子进程隔离 + PyMuPDF 降级 |
| `parsers/docx_parser.py` | python-docx，标题级别识别 |
| `parsers/xlsx_parser.py` | openpyxl，多 sheet 处理 |
| `parsers/md_parser.py` | markdown-it-py，图片引用解析 |

### 第 6-7 周：完善智能体

| 文件 | 说明 |
|------|------|
| `analyzer_agent.py` | 内容聚类 + 布局模式 + 文档类型识别 |
| `designer_agent.py` | 模板匹配 + 严格 replace-only |
| `fidelity_agent.py` | 四层完整校验（L1→L2→L3→L4） |
| `supplement_agent.py` | Pexels → Unsplash → AI 生图 降级策略 |

### 第 7-8 周：PDF 渲染 + 模板系统

| 文件 | 说明 |
|------|------|
| `exporters/pdf_renderer.py` | Playwright + WeasyPrint 混合 + PyPDF2 合并 |
| `templates/pdf/modern_tech/` | template.html + styles.css |
| `templates/pdf/elegant_minimal/` | 浅色极简模板 |
| `templates/pdf/business_professional/` | 商务模板 |
| `templates/pptx/elegant_minimal/` | SVG 模板集 |
| `templates/pptx/business_professional/` | SVG 模板集 |

### 第 8-9 周：前端增强

| 文件 | 说明 |
|------|------|
| `components/TemplateGallery.tsx` | 模板画廊 |
| `components/FidelityReport.tsx` | 四层保真报告可视化 |
| `components/DocumentPreview.tsx` | PDF.js 预览 |
| `components/AssetSupplement.tsx` | 素材补充面板 |
| `app/magazine/fidelity/page.tsx` | 保真报告页 |
| `app/magazine/supplement/page.tsx` | 素材补充页 |

### 阶段二验收标准

用户可上传任意格式文件，选择 3 种模板之一，输出 PDF 或 PPTX，查看保真报告，补充素材，预览结果。

---

## 阶段三：成品开发目标 — 生产级打磨（4 周）

**目标**: 测试覆盖 > 80%、CI/CD、性能优化、安全加固、一键部署。

### 第 10-11 周：测试体系

| 目录 | 说明 |
|------|------|
| `backend/app/tests/test_parsers/` | 5 个解析器单元测试 + 样本文件 |
| `backend/app/tests/test_agents/` | 6 个智能体单元测试 |
| `backend/app/tests/test_workflow/` | 端到端工作流测试 |
| `backend/app/tests/test_api/` | API 端点测试 |
| `frontend/src/__tests__/` | 组件 + 页面测试 |

### 第 11 周：CI/CD

| 文件 | 说明 |
|------|------|
| `.github/workflows/ci.yml` | lint + test + build |
| `.github/workflows/cd.yml` | Docker build + deploy |
| `.pre-commit-config.yaml` | 代码质量钩子 |

### 第 11-12 周：性能 + 安全

- Docling 子进程池
- Redis 缓存解析结果
- 前端代码分割 + 懒加载
- API 限流（slowapi）
- 文件类型深度验证
- 依赖漏洞扫描

### 第 12-13 周：部署自动化

| 文件 | 说明 |
|------|------|
| `scripts/deploy.sh` | 一键部署 |
| `scripts/backup.sh` + `restore.sh` | 备份恢复 |
| `docs/api.md` | API 文档 |
| `docs/deployment.md` | 部署指南 |
| `docs/development.md` | 开发指南 |

### 阶段三验收标准

`./scripts/deploy.sh` 一键部署成功，`pytest` 覆盖率 > 80%，CI/CD 自动化，安全扫描通过，并发 5 文件不卡顿。

---

## 总体估算

| 阶段 | 周期 | 新增文件 | 代码行数 |
|------|------|---------|---------|
| 阶段一：初始 MVP | 4 周 | ~36 | ~3,600 |
| 阶段二：迭代完善 | 5 周 | ~26 | ~7,500 |
| 阶段三：成品打磨 | 4 周 | ~31 | ~5,380 |
| **合计** | **13 周** | **~93** | **~16,480** |

## 可复用的 V1 代码

| V1 文件 | 可复用内容 | 目标 |
|---------|-----------|------|
| `services/parser.py` (472 行) | 5 格式解析 + 图文关联 | `parsers/*.py` |
| `services/zhipu_client.py` (142 行) | GLM-5 API 封装 | 直接增强 |
| `services/pdf_generator.py` (216 行) | 布局映射逻辑 | `exporters/pdf_renderer.py` |
| `api/router.py` (134 行) | API Key 加密存储 | 保留复用 |
| `core/redis.py` (27 行) | Redis 异步客户端 | 保留复用 |

## 关键文件优先级

1. `backend/app/models/unified_document.py` — 智能体通信基础
2. `backend/app/models/edit_actions.py` — 保真核心
3. `backend/app/workflow/magazine_pipeline.py` — 流程骨架
4. `backend/app/parsers/pptx_parser.py` — MVP 核心输入
5. `backend/app/exporters/ppt_master/svg_to_pptx.py` — MVP 核心输出
