# 杂志级文档重构智能体 V4 — 项目结构

> 基于 Presenton + PPTAgent + PPT Master 三项目集成

## 文件结构

```
弘天文档/
├── docker-compose-v4.yml           # V4 精简 Docker（4服务）
├── docker-compose.yml              # V1 原始（10服务，已过时）
├── .env.example                    # 环境变量模板
│
├── INTEGRATION_GUIDE_V4.md         # 集成指南（架构+接口+代码骨架）
├── IMPLEMENTATION_COMPLETE.md      # 完整实现代码（所有模块可直接使用）
├── ARCHITECTURE_V4_OPENSOURCE.md   # 开源项目选型论证
├── ARCHITECTURE_V3_FINAL.md        # V3 架构（修复V2的5个致命问题）
├── ARCHITECTURE_V2.md              # V2 架构（引入Playwright+LangGraph）
├── PROJECT_STRUCTURE.md            # 本文件
│
├── nginx/
│   └── nginx.conf                  # 反向代理配置
│
├── backend/                        # Python 后端
│   ├── requirements-v4.txt         # V4 依赖清单
│   ├── requirements.txt            # V1 依赖（已过时）
│   ├── Dockerfile
│   └── app/
│       ├── main.py                 # FastAPI 主入口
│       ├── core/
│       │   ├── config.py           # V4 配置管理
│       │   └── redis.py            # Redis 客户端
│       ├── api/
│       │   ├── __init__.py         # 路由注册
│       │   ├── router.py           # API Key 管理（V1）
│       │   └── v1/
│       │       └── magazine.py     # ★ V4 杂志重构 API
│       ├── models/                 # ★ 统一数据模型
│       │   ├── unified_document.py # UnifiedDocument / BoundingBox / Link
│       │   ├── edit_actions.py     # EditAction / MagazineEditPlan
│       │   └── design_spec.py      # DesignSpec / ColorScheme
│       ├── agents/                 # ★ 五个智能体
│       │   ├── parser_agent.py     # 解析路由（按格式分发）
│       │   ├── analyzer_agent.py   # 内容聚类 + 模式提取
│       │   ├── designer_agent.py   # 排版规划 + 编辑动作
│       │   ├── renderer_agent.py   # 双轨渲染路由
│       │   ├── fidelity_agent.py   # 四层保真校验
│       │   └── supplement_agent.py # 素材搜索 + AI 生图
│       ├── parsers/                # ★ 多格式解析器
│       │   ├── pptx_parser.py      # python-pptx
│       │   ├── pdf_parser.py       # Docling(子进程) + PyMuPDF
│       │   ├── docx_parser.py      # python-docx
│       │   ├── xlsx_parser.py      # openpyxl
│       │   └── md_parser.py        # markdown-it-py
│       ├── exporters/              # ★ 渲染引擎
│       │   ├── ppt_master/
│       │   │   ├── svg_to_pptx.py  # SVG → DrawingML → PPTX
│       │   │   └── finalize_svg.py # SVG 后处理流水线
│       │   └── pdf_renderer.py     # Playwright + WeasyPrint 混合
│       ├── workflow/
│       │   └── magazine_pipeline.py # ★ LangGraph 状态图
│       ├── services/               # V1 服务（保留兼容）
│       │   ├── parser.py           # V1 文档解析
│       │   ├── zhipu_client.py     # GLM-5 API 封装
│       │   └── pdf_generator.py    # V1 PDF 生成
│       ├── templates/              # ★ 杂志模板库
│       │   ├── pdf/
│       │   │   └── modern_tech/
│       │   │       ├── template.html
│       │   │       ├── styles.css
│       │   │       └── config.json
│       │   └── pptx/
│       │       └── modern_tech/
│       │           ├── template.pptx
│       │           ├── pages/
│       │           │   ├── cover.svg
│       │           │   ├── content_text.svg
│       │           │   ├── content_image_text.svg
│       │           │   └── data_card.svg
│       │           └── config.json
│       └── tests/
│           └── test_parse.py
│
└── frontend/                       # Next.js 前端（Presenton）
    ├── Dockerfile
    ├── package.json
    └── src/
        ├── lib/
        │   ├── store.ts            # Zustand 状态管理
        │   └── api.ts              # API 调用封装
        ├── components/
        │   ├── FidelityReport/     # ★ 保真度可视化
        │   ├── DocumentPreview/    # ★ 文档预览
        │   ├── TemplateGallery/    # ★ 模板选择器
        │   └── AssetSupplement/    # ★ 素材补充面板
        └── pages/
            ├── import/             # ★ 多格式导入页
            └── magazine/           # ★ 杂志重构流程页
```

## V1 → V4 演进对比

| 维度 | V1 | V4 |
|------|----|----|
| Docker 服务数 | 10 | 4 |
| AI 处理 | Dify + 本地模型 | GLM-5 API（零 GPU） |
| PDF 渲染 | Typst | Playwright + WeasyPrint |
| PPTX 生成 | python-pptx 从零构建 | PPT Master SVG→DrawingML |
| 内容保真 | 无校验 | 四层保真校验 |
| 工作流编排 | Dify 可视化 | LangGraph 代码编排 |
| 解析器 | 内联函数 | 独立模块 + 子进程隔离 |
| 模板 | 代码内嵌 | 外部文件 + config.json |

## 核心流程（V4）

```
1. API Key 配置  → 前端输入，加密存 Redis（24h 过期）
2. 文件上传      → 后端接收，按格式路由到对应解析器
3. 文档解析      → Parser Agent: PPTX→python-pptx, PDF→Docling+PyMuPDF, 等
4. 图文关联      → 三重策略：空间距离 + 结构关键词 + 语义关联(GLM-5)
5. 内容分析      → Analyzer Agent: 聚类 + 模式提取 (PPTAgent 思想)
6. 排版设计      → Designer Agent: 只替换不重写 (edit-based, PPTAgent 核心)
7. 素材补充      → Supplement Agent: Pexels → Unsplash → AI 生图 (降级策略)
8. 渲染生成      → Renderer Agent: PDF(Playwright+WeasyPrint) 或 PPTX(PPT Master)
9. 保真校验      → Fidelity Agent: L1指纹 → L2关联 → L3语义 → L4人工
10. 预览导出     → 前端预览 + 下载
```

## 关键设计决策

- **原始文件和图片永不离开本地服务器**
- **发送给智谱的只有脱敏后的纯文本摘要**
- **API Key 不持久化，24 小时自动删除**
- **编辑动作只替换不重写，确保内容 100% 保真**
- **Docling 在子进程中运行，防止内存泄漏**
- **混合 PDF 引擎解决 Chromium 表格分页 bug**
