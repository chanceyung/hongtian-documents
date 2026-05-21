# 开发指南

## 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端框架 | FastAPI | Python 3.11+，异步 |
| 状态管理 | Pydantic V2 | 数据模型和验证 |
| 工作流 | LangGraph | 智能体编排 |
| LLM | GLM-5（智谱） | 内容分析和设计 |
| 前端 | Next.js 15 + React 19 | TypeScript strict |
| 状态 | Zustand | 客户端状态管理 |
| 样式 | Tailwind CSS | 原子化 CSS |
| 缓存 | Redis | API Key + 解析缓存 |
| PDF 渲染 | Playwright + WeasyPrint | 混合双引擎 |
| PPTX 渲染 | SVG → DrawingML | PPT Master 方案 |

## 开发环境搭建

```bash
# 自动搭建
./scripts/setup-dev.sh

# 或手动搭建
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-v4.txt
playwright install chromium

cd ../frontend
npm install
```

## 项目结构

```
backend/app/
├── agents/          # 6 个智能体
├── api/             # API 路由
│   └── v1/          # V4 杂志重构 API
├── core/            # 配置、Redis、缓存
├── exporters/       # 渲染引擎
│   ├── ppt_master/  # SVG → PPTX
│   └── pdf_renderer # 混合 PDF
├── models/          # 统一数据模型
├── parsers/         # 5 格式解析器
├── services/        # V1 兼容服务
├── templates/       # 3 套模板（PDF + PPTX）
└── workflow/        # LangGraph 工作流

frontend/src/
├── app/             # Next.js 页面
├── components/      # 6 个 UI 组件
└── lib/             # API 封装 + 状态管理
```

## 六智能体架构

```
Parser Agent    → 格式路由 + 解析 → UnifiedDocument
Analyzer Agent  → 内容聚类 + 模式提取
Designer Agent  → 编辑动作生成（replace-only）
Supplement Agent → 素材补充（Pexels → Unsplash → AI）
Renderer Agent  → 双轨渲染（PDF / PPTX）
Fidelity Agent  → 四层保真校验（L1→L2→L3→L4）
```

## 代码规范

- Python: type annotations + Pydantic V2 + async/await
- TypeScript: strict mode + 函数组件 + Hooks
- 不写 what 注释，只写 why 注释
- 提交信息：中文，格式 `类型(范围): 描述`

## 运行测试

```bash
cd backend
pytest tests/ -v

# 带覆盖率
pytest tests/ --cov=app --cov-report=html
```

## 添加新模板

1. 创建目录 `templates/pptx/<模板名>/pages/`
2. 制作 4 个 SVG 页面（cover, content_text, content_image_text, data_card）
3. 创建 `config.json`
4. SVG 必须遵守 PPT Master 规范：viewBox、无 mask、inline style
5. 深色背景用 White Logo，浅色用 Black Logo
