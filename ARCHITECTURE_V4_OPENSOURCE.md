# 杂志级文档重构智能体 V4 — 基于成熟开源项目的生产级方案

> 核心策略转变：从"从零构建"变为"站在巨人肩膀上"。
> 基于三个成熟开源项目改造，而非自己写每一行代码。
> 预计节省 60% 开发工作量，同时获得更高的稳定性。

---

## 零、策略转变：为什么基于现有项目

| 现有项目 | 解决什么问题 | Star | 我们要改什么 |
|---------|-------------|------|------------|
| **PPTAgent** (中科院) | PPTX 智能重设计引擎，两阶段编辑 | 论文级 | 替换LLM为GLM-5、增加PDF/Word输入 |
| **PPT Master** | SVG→DrawingML 原生PPTX生成 | 活跃 | 集成其PPTX输出引擎 |
| **Presenton** | 完整的前后端UI + Docker部署 | 社区认可 | 集成为前端、对接我们的后端 |

**关键洞察**：PPTAgent 的"两阶段编辑方法"完美解决了核心需求——它不重写内容，而是基于参考模板编辑替换内容，天然保证内容完整性。

---

## 一、系统架构（基于三个开源项目组合）

```
┌──────────────────────────────────────────────────────────────┐
│                 Presenton 前端（改造）                         │
│  Next.js + React + TailwindCSS + Zustand                     │
│  ★ 已有：文件上传 / 模板选择 / 幻灯片编辑器 / PPTX导出       │
│  ★ 已有：API Key 管理 (BYOK) / Docker部署                    │
│  ★ 改造：增加PDF导出 / 内容保真报告 / 素材补充面板           │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│              FastAPI 后端（Presenton已有 + 扩展）              │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  PPTAgent 核心（改造）—— PPTX 重设计引擎               │  │
│  │                                                        │  │
│  │  阶段I：文档分析                                       │  │
│  │  ├─ 幻灯片聚类（ViT嵌入+层次聚类）                    │  │
│  │  ├─ 布局模式提取（Category+Description+Content）      │  │
│  │  └─ 图文关联分析                                      │  │
│  │                                                        │  │
│  │  阶段II：基于编辑的生成                                │  │
│  │  ├─ 大纲生成（GLM-5）                                  │  │
│  │  ├─ 参考模板匹配（从杂志模板库选）                    │  │
│  │  ├─ HTML表示编辑（replace_span/add/delete）           │  │
│  │  └─ 自我纠错循环（REPL环境）                          │  │
│  │                                                        │  │
│  │  ★ 改造：GLM-5替换GPT-4o/Qwen                         │  │
│  │  ★ 改造：增加PDF/Word/Excel/MD输入支持                │  │
│  │  ★ 改造：增加四层保真校验                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────┐  ┌───────────────────────────────┐ │
│  │  PDF 生成引擎（新建） │  │  PPT Master 输出引擎（集成） │ │
│  │  视觉页 → Playwright │  │  SVG → DrawingML 转换        │ │
│  │  文字页 → WeasyPrint │  │  原生可编辑PPTX              │ │
│  │  合并 → PyPDF        │  │  ★ 已有完整的转换实现        │ │
│  └──────────────────────┘  └───────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  内容保真校验管线（V3设计，保持不变）                   │  │
│  │  L1:内容指纹 → L2:图文关联 → L3:语义对比 → L4:人工确认 │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│  基础设施（Presenton已有Docker Compose）                     │
│  Backend │ Frontend │ Redis │ SQLite/PostgreSQL              │
└──────────────────────────────────────────────────────────────┘
```

---

## 二、三个基础项目详解及改造方案

### 2.1 Presenton — 前端 + 后端骨架

**已有功能（直接用）**：
- Next.js + React + TailwindCSS 前端
- FastAPI 后端
- 文件上传界面
- 模板选择系统（HTML + Tailwind 模板）
- 幻灯片编辑器
- PPTX 导出（完全可编辑）
- BYOK（用户自带API Key）系统
- Docker 一键部署
- 多模型支持（OpenAI/Gemini/Claude/自定义端点）
- Electron 桌面应用支持

**需要改造的部分**：

```bash
# 1. 添加智谱 GLM-5 支持（利用已有的自定义端点功能）
# Presenton 已支持 CUSTOM_LLM_URL，只需配置：
CUSTOM_LLM_URL=https://open.bigmodel.cn/api/paas/v4
CUSTOM_MODEL=glm-5-pro

# 2. 添加 PDF 导出功能
# Presenton 目前只有 PPTX 导出，需要增加 PDF 导出
# 在 backend/app/exporters/ 下增加 pdf_exporter.py

# 3. 添加文件类型路由（PPTAgent只处理PPTX，我们需要支持所有格式）
# 在 backend/app/parsers/ 下增加多格式解析器
```

**改造工作量**：约 2 周

### 2.2 PPTAgent — PPTX 智能重设计核心

**已有功能（直接用）**：
- 两阶段编辑框架（分析 → 生成）
- 幻灯片聚类和模式提取（ViT嵌入）
- 基于编辑的生成（replace_span、add、delete）
- HTML表示简化修改
- 自我纠错机制（REPL环境）
- DeepPresenter 微调模型（9B参数）
- 参考模板匹配

**核心优势**：
> PPTAgent 不是"重写"PPT，而是"编辑"已有模板。
> 这意味着原始内容被**替换**到新的设计布局中，而不是被AI重新生成。
> 这是保证"内容忠于原意"的最可靠方法。

**需要改造的部分**：

```python
# 1. 替换 LLM 后端为 GLM-5
# 原始配置使用 GPT-4o / Qwen2.5-72B
# 改为使用 GLM-5 Pro API

# deeppresenter/config.yaml 改造
models:
  lm:
    provider: "custom_openai"
    model: "glm-5-pro"
    api_base: "https://open.bigmodel.cn/api/paas/v4"
    api_key: "${GLM_API_KEY}"
  vm:  # 视觉模型
    provider: "custom_openai"
    model: "glm-5v"  # 智谱视觉模型
    api_base: "https://open.bigmodel.cn/api/paas/v4"
    api_key: "${GLM_API_KEY}"

# 2. 添加多格式输入支持
# PPTAgent 原本只接受PPTX和PDF（通过MinerU）
# 需要增加 Word/Excel/Markdown 输入

# 在 pptagent/parsers/ 下增加：
# - docx_parser.py  （基于 python-docx）
# - xlsx_parser.py  （基于 openpyxl）
# - md_parser.py    （基于 markdown-it-py）

# 3. 增加内容保真校验
# 在生成阶段后增加校验节点

# 4. 替换视觉模型
# PPTAgent 使用 ViT 做幻灯片聚类
# 可以替换为 GLM-5V 做更精准的布局理解
```

**关键改造：将72B本地模型替换为API调用**：
```python
# PPTAgent 原本需要 A100 GPU 跑 Qwen2.5-72B
# 我们改为通过 API 调用 GLM-5 Pro（零GPU）

class GLM5Backend:
    """替换 PPTAgent 的本地模型为 GLM-5 API"""

    def __init__(self, api_key: str):
        import httpx
        self.client = httpx.AsyncClient(
            base_url="https://open.bigmodel.cn/api/paas/v4",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=120,
        )

    async def analyze_slides(self, slides_content: list[str]) -> dict:
        """阶段I：分析幻灯片（替换原本的本地LLM调用）"""
        import instructor
        from pydantic import BaseModel

        class SlideAnalysis(BaseModel):
            slide_types: list[str]
            layout_patterns: list[dict]
            content_groups: list[list[int]]

        # 使用 Instructor 保证结构化输出
        ...
        return analysis

    async def generate_edit_actions(self, content: str, reference_slide_html: str) -> list[str]:
        """阶段II：生成编辑动作（替换原本的本地LLM调用）"""
        prompt = f"""基于以下参考幻灯片的HTML表示，生成编辑动作将内容替换为新内容。
只允许 replace_span 操作，不允许删除或添加新元素。

参考幻灯片HTML:
{reference_slide_html}

新内容:
{content}

输出：Python代码列表，每个元素是一个编辑动作。"""

        response = await self.client.post(
            "/chat/completions",
            json={
                "model": "glm-5-pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
        )
        return self._parse_actions(response.json())

    async def self_correct(self, failed_action: str, error_msg: str) -> str:
        """自我纠错（PPTAgent的核心特性，保留）"""
        prompt = f"""以下编辑动作执行失败：
动作: {failed_action}
错误: {error_msg}

请修正这个动作。"""
        response = await self.client.post(
            "/chat/completions",
            json={
                "model": "glm-5-pro",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            }
        )
        return response.json()["choices"][0]["message"]["content"]
```

**改造工作量**：约 3 周

### 2.3 PPT Master — SVG→DrawingML PPTX 输出引擎

**已有功能（直接用）**：
- SVG → DrawingML 转换器（核心技术）
- 原生 PowerPoint 形状生成
- 模板提取系统（从任意PPTX提取模板）
- 中文完整支持
- 图片搜索（Pexels/Pixabay/Openverse）
- AI 图片生成集成
- 实时预览服务器

**集成方案**：

```python
# 将 PPT Master 的 SVG→DrawingML 转换器作为独立模块集成
# 路径：backend/app/exporters/pptx_exporter.py

from ppt_master.svg_to_pptx import svg_to_pptx
from ppt_master.finalize_svg import finalize_svg
from ppt_master.create_template import extract_template

class PPTMasterExporter:
    """使用 PPT Master 的引擎输出原生可编辑 PPTX"""

    async def export(self, slides_html: list[str], template_path: str) -> Path:
        """
        1. PPTAgent 生成每页的 HTML/SVG 设计
        2. PPT Master 将 SVG 转换为 DrawingML
        3. 输出原生可编辑 PPTX
        """
        # Step 1: HTML → SVG（PPTAgent的HTML表示 → PPT Master的SVG）
        svg_slides = []
        for html in slides_html:
            svg = self._html_to_svg(html)
            svg_slides.append(svg)

        # Step 2: SVG → DrawingML → PPTX（使用PPT Master的核心转换）
        output_path = svg_to_pptx(
            svg_slides=svg_slides,
            template_path=template_path,
            output_dir="exports/",
        )

        return output_path

    def extract_template_from_pptx(self, source_pptx: str) -> str:
        """从任意PPTX提取模板（PPT Master已有功能）"""
        return extract_template(source_pptx, output_dir="templates/")
```

**改造工作量**：约 1 周

---

## 三、改造后的完整工作流

```
用户上传文件（PPTX/PDF/Word/Excel/MD）
         │
         ▼
┌─ 文件类型路由器（V3设计，按格式选解析器）──┐
│  PPTX → python-pptx（最稳定）              │
│  PDF  → Docling子进程（隔离）+ PyMuPDF降级  │
│  DOCX → python-docx                        │
│  XLSX → pandas + openpyxl                  │
│  MD   → markdown-it-py                     │
└─────────────────────────────────────────────┘
         │
         ▼ 统一输出：结构化JSON + 素材文件 + 图文关联表 + 内容指纹
         │
         ▼
┌─ PPTAgent 核心改造（★ 主要改造点）────────┐
│                                             │
│  阶段I：文档分析（GLM-5 API）               │
│  ├─ 内容聚类（按主题/页面分组）             │
│  ├─ 布局模式提取（每页的元素结构）         │
│  └─ 图文关联确认（三重策略投票）           │
│                                             │
│  阶段II：基于编辑的生成（GLM-5 API）        │
│  ├─ 大纲生成（保持原文结构）               │
│  ├─ 从杂志模板库匹配最合适的模板           │
│  ├─ 生成编辑动作（只替换，不重写）★        │
│  │   └─ replace_span：替换文字内容         │
│  │   └─ replace_image：替换图片            │
│  │   └─ 绝不 delete/add（保证完整性）★     │
│  └─ 自我纠错循环（失败 → 修正 → 重试）    │
│                                             │
└─────────────────────────────────────────────┘
         │
         ▼
┌─ 素材补充（缺图时）────────────────────────┐
│  Unsplash/Pexels搜索 → rembg去背景          │
│  搜索不到 → Replicate FLUX.1生图            │
└─────────────────────────────────────────────┘
         │
         ├── 输出 PPTX ──→ PPT Master SVG→DrawingML → 原生可编辑PPTX
         │
         └── 输出 PDF  ──→ 混合引擎（Playwright视觉页 + WeasyPrint文字页）
         │
         ▼
┌─ ★ 四层保真校验（V3设计，保持不变）────────┐
│  L1: 内容指纹完整性（文字零遗漏、图片零丢失）│
│  L2: 图文关联完整度（对应关系零错位）       │
│  L3: 语义保真校验（GLM-5 API对比）         │
│  L4: 人工确认机制（低置信度标记）           │
│  不达 95% → 自动修复 → 重新校验（最多2次）  │
└─────────────────────────────────────────────┘
         │
         ▼
      最终输出：杂志级 PDF 或 可编辑 PPTX
```

---

## 四、关键创新：PPTAgent 的"编辑式"方法如何保证内容保真

传统方法（从零生成）：
```
原文 → LLM总结/改写 → 填入模板 → 可能丢内容/改意思 ❌
```

PPTAgent方法（基于编辑）：
```
原文 → 选择杂志模板 → 只替换文字/图片到模板 → 内容原封不动 ✅
```

**具体实现**：

```python
# PPTAgent 的编辑动作示例
# 假设参考模板有一页"产品介绍"布局

# 原始模板HTML:
# <span class="title">【产品名称】</span>
# <span class="desc">【产品描述】</span>
# <img class="product-img" src="placeholder.jpg" />

# PPTAgent 生成的编辑动作：
actions = [
    "replace_span('.title', 'SmartAI 智能助手')",           # 原文直接替换
    "replace_span('.desc', '基于大模型的新一代智能助手')",   # 原文直接替换
    "replace_image('.product-img', 'extracted_img_001.jpg')", # 原图直接替换
]

# ★ 关键：没有任何"生成新文字"的动作
# ★ 所有的 replace 操作都使用原文内容
# ★ 这就是内容保真的根本保证
```

---

## 五、具体改造步骤（文件级别）

### Step 1：Fork Presenton，建立项目基础

```bash
# 克隆 Presenton
git clone https://github.com/presenton/presenton.git doc-magazine-agent
cd doc-magazine-agent

# 项目结构（已有）
# ├── frontend/          # Next.js 前端
# ├── backend/           # FastAPI 后端
# ├── docker-compose.yml # Docker 部署
# └── Dockerfile
```

### Step 2：集成 PPTAgent 核心模块

```bash
# 将 PPTAgent 核心复制到后端
git clone https://github.com/icip-cas/PPTAgent.git /tmp/pptagent

# 只提取核心模块（不需要它的前端和CLI）
cp -r /tmp/pptagent/deeppresenter/ backend/app/pptagent_core/
cp -r /tmp/pptagent/pptagent/ backend/app/pptagent_cli/
```

**改造后的 backend 目录结构**：
```
backend/
├── app/
│   ├── main.py                    # Presenton 已有
│   ├── api/                       # Presenton 已有
│   │   ├── routes/
│   │   │   ├── presentations.py   # 已有（PPTX生成）
│   │   │   ├── pdf_export.py      # ★ 新增（PDF导出）
│   │   │   └── fidelity.py        # ★ 新增（保真校验）
│   │   └── deps.py
│   ├── pptagent_core/             # ★ 从PPTAgent集成
│   │   ├── analyzer/              # 阶段I：文档分析
│   │   │   ├── slide_cluster.py   # 幻灯片聚类
│   │   │   ├── pattern_extract.py # 模式提取
│   │   │   └── linkage.py         # 图文关联
│   │   ├── generator/             # 阶段II：基于编辑的生成
│   │   │   ├── outline.py         # 大纲生成
│   │   │   ├── editor.py          # 编辑动作生成
│   │   │   └── self_correct.py    # 自我纠错
│   │   ├── models/                # ★ 新增：GLM-5后端
│   │   │   ├── glm5_backend.py    # 替换原始LLM
│   │   │   └── glm5v_backend.py   # 替换原始视觉模型
│   │   └── config.yaml            # ★ 改造：GLM-5配置
│   ├── parsers/                   # ★ 新增：多格式解析
│   │   ├── router.py              # 文件类型路由
│   │   ├── pptx_parser.py         # PPTX解析
│   │   ├── pdf_parser.py          # PDF解析（Docling子进程）
│   │   ├── docx_parser.py         # Word解析
│   │   ├── xlsx_parser.py         # Excel解析
│   │   └── md_parser.py           # Markdown解析
│   ├── exporters/                 # 导出引擎
│   │   ├── pptx_exporter.py       # ★ 集成PPT Master的SVG→DrawingML
│   │   ├── pdf_exporter.py        # ★ 新增：混合PDF引擎
│   │   └── fidelity.py            # ★ 新增：四层保真校验
│   ├── assets/                    # 素材管理
│   │   ├── supplementer.py        # ★ 新增：多源素材补充
│   │   └── search.py              # Unsplash/Pexels搜索
│   └── templates/                 # 杂志模板库
│       ├── pptx/                  # PPTX模板（设计师制作）
│       │   ├── product-intro/
│       │   ├── company-profile/
│       │   └── marketing-brochure/
│       └── pdf/                   # PDF模板（HTML/CSS）
│           ├── magazine-tech/
│           ├── magazine-business/
│           └── product-catalog/
```

### Step 3：集成 PPT Master 的输出引擎

```bash
# 克隆 PPT Master
git clone https://github.com/hugohe3/ppt-master.git /tmp/ppt-master

# 只提取 SVG→DrawingML 转换器
cp -r /tmp/ppt-master/svg_to_pptx.py backend/app/exporters/
cp -r /tmp/ppt-master/finalize_svg.py backend/app/exporters/
cp -r /tmp/ppt-master/create_template.py backend/app/exporters/
```

### Step 4：修改 Presenton 前端

```
frontend/  (Presenton 已有)
├── src/
│   ├── app/
│   │   ├── create/           # 已有：创建演示文稿
│   │   ├── edit/             # 已有：编辑幻灯片
│   │   ├── import/           # ★ 改造：增加多格式导入（不只是PPTX）
│   │   ├── templates/        # 已有：模板选择
│   │   ├── fidelity/         # ★ 新增：内容保真报告页面
│   │   └── export/           # ★ 改造：增加PDF导出选项
│   ├── components/
│   │   ├── Editor/           # 已有：幻灯片编辑器
│   │   ├── Upload/           # 已有：文件上传
│   │   ├── FidelityReport/   # ★ 新增：保真度可视化
│   │   └── AssetSupplement/  # ★ 新增：素材补充面板
│   └── lib/
│       ├── api.ts            # 已有
│       └── store.ts          # 已有（Zustand）
```

---

## 六、Docker Compose（基于 Presenton 已有配置）

```yaml
# 基于 Presenton 的 docker-compose.yml 改造
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      # Presenton 已有的配置
      - DATABASE_URL=sqlite:///./app_data/presenton.db
      - LLM=custom
      - CUSTOM_LLM_URL=https://open.bigmodel.cn/api/paas/v4
      - CUSTOM_MODEL=glm-5-pro
      # ★ 新增配置
      - GLM_VISION_MODEL=glm-5v
      - UNSPLASH_ACCESS_KEY=${UNSPLASH_KEY}
      - PEXELS_API_KEY=${PEXELS_KEY}
      - REPLICATE_API_TOKEN=${REPLICATE_KEY}
      - FIDELITY_THRESHOLD=0.95
    volumes:
      - ./app_data:/app/app_data
      - ./templates:/app/app/templates

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  redis:
    image: redis:7-alpine
    # Presenton 已使用 Redis 做任务队列

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
```

---

## 七、开发计划（5周，比V3再缩短2周）

| 周 | 任务 | 基于什么 | 新增工作量 |
|----|------|---------|-----------|
| **1** | Fork Presenton，配置GLM-5，跑通基础流程 | Presenton | 配置+测试 |
| **2** | 集成PPTAgent核心，改造LLM后端为GLM-5 | PPTAgent | 改造模型层 |
| **3** | 集成PPT Master输出引擎，实现PPTX导出 | PPT Master | 集成接口 |
| **4** | 实现PDF混合引擎 + 四层保真校验 + 素材补充 | V3设计 | 新开发 |
| **5** | 前端改造（导入页面/保真报告/导出选项）+ 全面测试 | Presenton UI | UI改动 |

---

## 八、风险与应对

| 风险 | 可能性 | 应对 |
|------|--------|------|
| PPTAgent 的编辑动作格式与 GLM-5 不兼容 | 中 | PPTAgent 已用 OpenAI 兼容格式，GLM-5 兼容 |
| PPT Master 的 SVG→DrawingML 转换有边界情况 | 中 | PPT Master 已持续迭代，保持同步更新 |
| Presenton 版本更新导致 fork 冲突 | 低 | 锁定版本，按需 cherry-pick 上游更新 |
| PPTAgent 的 ViT 聚类需要本地模型 | 低 | 替换为 GLM-5V API 做视觉理解 |
| 模板库不够丰富 | 高 | 初期提供 5-8 套核心模板，持续请设计师补充 |

---

## 九、V4 vs V3 vs V2 vs V1 最终对比

| 维度 | V1 | V2 | V3 | **V4（最终）** |
|------|----|----|-----|---------------|
| 前端 | 自建Next.js | 自建Next.js | 自建Next.js | **Fork Presenton** |
| PPTX重设计 | 无 | 无 | python-pptx模板填充 | **PPTAgent编辑式** |
| PPTX输出 | python-pptx | python-pptx | 模板填充 | **PPT Master SVG→DrawingML** |
| PDF生成 | Typst | Playwright | 混合引擎 | **混合引擎（保持）** |
| 工作流 | Dify | LangGraph | LangGraph | **LangGraph（保持）** |
| 保真校验 | 无 | 简单 | 四层校验 | **四层校验（保持）** |
| 开发周期 | 8周 | 6周 | 7周 | **5周** |
| 新代码量 | ~15000行 | ~12000行 | ~14000行 | **~6000行** |
| 稳定性 | 低 | 中 | 高 | **最高（基于成熟项目）** |
| 杂志级质量 | 中 | 高 | 高 | **最高（编辑式方法）** |

---

## 十、核心优势总结

1. **站在巨人肩膀上**：三个成熟开源项目组合，6000行新代码（vs V1的15000行）
2. **PPTAgent编辑式方法天然保证内容保真**：只替换不重写，从根本上解决"忠于原意"
3. **PPT Master原生可编辑PPTX输出**：SVG→DrawingML，质量远超python-pptx
4. **Presenton完整UI和Docker部署**：无需从零搭建前端
5. **智谱GLM-5无缝集成**：Presenton已支持自定义OpenAI兼容端点
6. **四层保真校验兜底**：即使编辑式方法有偏差，校验管线也能捕获
7. **5周开发周期**：比从零构建缩短40%
