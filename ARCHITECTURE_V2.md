# 杂志级文档重构智能体 V2 — 重构方案

> 核心目标：客户上传 PPTX/PDF/Word/Excel/Markdown → 系统解析素材、图片、文字及对应关系
> → 重新组合生成杂志级精美 PDF/PPTX → 素材不足部分通过网络搜索/AI生图弥补
>
> 核心承诺：图片-文字对应关系不改变，语义忠于原意

---

## 一、为什么重构？V1 vs V2 关键变化

| 模块 | V1 方案 | 问题 | V2 方案 | 改进 |
|------|---------|------|---------|------|
| 文档解析 | Unstructured.IO + PyMuPDF + python-pptx | 多个引擎拼接，关联逻辑自写 | **Docling (IBM)** | 统一引擎，原生支持PDF/DOCX/PPTX/XLSX，自带坐标和结构 |
| PDF生成 | Typst | 不支持CSS、图文混排差、设计师不会 | **Playwright + Paged.js** | 完整CSS支持，3ms渲染，模板=HTML文件 |
| 工作流编排 | Dify + Next.js | 职责重叠，10个Docker容器 | **LangGraph** | 纯Python，6个容器，无冗余 |
| 素材搜索 | SerpAPI | 搜索结果非素材专用 | **Unsplash + Pexels + Pixabay API** | 专业素材库，CC0免费商用 |
| AI生图 | Flux.1 API 单一 | 需要自建或单一接口 | **Replicate API (多模型)** | 支持FLUX/SD3等，按量付费 |
| 图片处理 | 无 | — | **rembg + smartcrop** | 去背景+智能裁剪 |
| LLM结构化输出 | 手写prompt+JSON解析 | 不稳定 | **Instructor** | Pydantic强类型，100%结构化 |

---

## 二、V2 系统架构（6个容器，零GPU）

```
┌──────────────────────────────────────────────────────────────┐
│                    用户浏览器                                  │
│  Next.js 前端（文件上传 / 预览 / 模板选择 / 自然语言调整）    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               FastAPI 后端（单进程，纯Python）                │
│                                                              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  API Key     │  │ LangGraph    │  │  Docling           │  │
│  │  安全管理    │  │ 工作流引擎   │  │  文档解析(IBM)     │  │
│  │  (Redis会话) │  │              │  │  ★ 统一入口        │  │
│  └─────────────┘  └──────┬───────┘  └────────────────────┘  │
│                          │                                   │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │  智谱GLM-5   │  │ Instructor   │  │  素材补充系统      │  │
│  │  + Instructor│  │ 结构化输出   │  │  Unsplash/Pexels   │  │
│  │  (语义分析)  │  │ (Pydantic)   │  │  Replicate(生图)   │  │
│  └─────────────┘  └──────────────┘  │  rembg(去背景)     │  │
│                                      └────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              PDF/PPTX 生成引擎                        │   │
│  │  PDF:  HTML/CSS模板 → Playwright + Paged.js → PDF   │   │
│  │  PPTX: python-pptx（保留）                           │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                     基础设施（6个容器）                       │
│  Redis │ MinIO │ Playwright │ Docling │ Frontend │ Backend  │
│  (会话) │ (文件) │ (PDF渲染)  │ (解析)  │  (UI)    │  (API)  │
└──────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│               用户自付 API（用户自填Key）                      │
│  智谱GLM-5 Pro（文本分析）│ Replicate（AI生图）               │
│  智谱GLM-5V（图片理解）  │ Unsplash/Pexels（素材搜索）       │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块详细设计

### 模块1：Docling 统一文档解析引擎（替换所有解析器）

**为什么选 Docling**：
- IBM Research 开源，7300+ Star，每日更新
- **一个库**统一解析 PDF/DOCX/PPTX/XLSX/HTML/图片
- 原生输出**带坐标的结构化JSON**（bounding box、阅读顺序）
- 自带 TableFormer 表格结构识别
- 自带 DocLayNet 布局分析模型
- 输出 LLM-ready 格式

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat

# 一个转换器处理所有格式
converter = DocumentConverter(
    allowed_formats=[
        InputFormat.PDF,
        InputFormat.DOCX,
        InputFormat.PPTX,
        InputFormat.XLSX,
        InputFormat.HTML,
        InputFormat.IMAGE,
    ]
)

result = converter.convert("客户文档.pptx")

# 获取带坐标的结构化输出
for item, text_level in result.document.iterate_items():
    # item 包含：内容、坐标(bbox)、类型(文字/图片/表格)、页码
    print(f"类型: {item.label}, 坐标: {item.prov}, 内容: {item.text}")

# 导出为 Markdown（保留图片引用）
markdown = result.document.export_to_markdown()

# 导出为带坐标的 JSON
doc_dict = result.document.export_to_dict()
```

**图片-文字关联**（Docling 原生 + 增强）：
- Docling 自带空间位置关联（同页、相邻元素）
- 我们增加：语义关联（智谱 Embedding API）、结构关联（标题→图片→图注）
- 三重策略投票，置信度 < 0.6 标记为"需人工确认"

### 模块2：Playwright + Paged.js PDF 生成（替换 Typst）

**为什么选 Playwright**：
- 完整 Chromium CSS 引擎：Grid、Flexbox、shape-outside 全支持
- **3ms/页**（warm模式），比 WeasyPrint 快 75 倍
- 模板 = 普通 HTML/CSS 文件，任何前端开发者都能写
- Paged.js 补充分页控制：命名页面、页眉页脚、目录、交叉引用

```python
from playwright.async_api import async_playwright

async def generate_magazine_pdf(html_content: str, output_path: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # 加载 HTML 模板（含 Paged.js 分页脚本）
        await page.set_content(html_content)

        # 注入 Paged.js 进行分页预处理
        await page.add_script_tag(url="https://unpkg.com/pagedjs/dist/paged.polyfill.js")
        await page.wait_for_selector(".pagedjs_page")  # 等待分页完成

        # 生成 PDF
        await page.pdf(
            path=output_path,
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()
```

**杂志级排版模板示例**（HTML/CSS）：
```html
<!-- templates/magazine-tech/product-intro.html -->
<!DOCTYPE html>
<html>
<head>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;700;900&display=swap');

@page {
    size: A4;
    margin: 15mm 12mm;
    @bottom-center { content: counter(page); font-size: 9pt; color: #888; }
}

@page cover {
    margin: 0;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

@page section-start {
    margin-top: 25mm;
}

/* 封面页 */
.cover-page { page: cover; }
.cover-title {
    font-family: 'Noto Sans SC', sans-serif;
    font-weight: 900; font-size: 48pt;
    color: white;
    position: absolute; top: 40%; left: 12mm;
    text-shadow: 2px 4px 20px rgba(0,0,0,0.3);
}
.cover-image {
    position: absolute; right: 0; top: 20%;
    width: 55%; height: auto;
    clip-path: polygon(15% 0, 100% 0, 100% 100%, 0 100%);
}

/* 内容页 - 双栏布局 */
.content-page { columns: 2; column-gap: 8mm; }
.content-page img {
    width: 100%; break-inside: avoid;
    border-radius: 4px;
    margin-bottom: 4mm;
}

/* 重点突出框 */
.highlight-box {
    background: #f0f4ff; border-left: 4px solid #0f3460;
    padding: 4mm; margin: 4mm 0;
    break-inside: avoid;
    font-size: 10pt; line-height: 1.6;
}

/* 数据卡片 */
.data-card {
    display: grid; grid-template-columns: 1fr 1fr;
    gap: 3mm; break-inside: avoid;
}
.data-item {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white; padding: 4mm; border-radius: 4mm;
    text-align: center;
}
.data-value { font-size: 24pt; font-weight: 900; }
.data-label { font-size: 8pt; opacity: 0.8; }
</style>
</head>
<body>
    <!-- 由 LangGraph 工作流动态填充 -->
    <div class="cover-page">
        <img class="cover-image" src="{{cover_image}}" />
        <h1 class="cover-title">{{document_title}}</h1>
    </div>
    <!-- 更多页面... -->
</body>
</html>
```

### 模块3：LangGraph 工作流引擎（替换 Dify）

**为什么选 LangGraph**：
- 31,500+ Star，2025年10月发布 v1.0 稳定版
- 纯 Python，零额外基础设施
- 状态图模式，天然适合文档处理管线
- 原生支持异步、并行、人工审批节点

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class DocumentState(TypedDict):
    file_path: str
    session_id: str
    # Docling 解析结果
    parsed_elements: list[dict]
    image_text_linkage: list[dict]
    # 智谱分析结果
    document_structure: dict
    layout_plan: dict
    # 素材
    supplemented_assets: list[dict]
    # 生成结果
    output_path: str
    # 校验
    quality_score: float
    needs_review: bool

def build_document_pipeline() -> StateGraph:
    graph = StateGraph(DocumentState)

    # 节点定义
    graph.add_node("parse_document", parse_with_docling)
    graph.add_node("link_content_assets", build_linkage)
    graph.add_node("analyze_semantics", analyze_with_zhipu)
    graph.add_node("plan_layout", plan_magazine_layout)
    graph.add_node("supplement_assets", find_or_generate_assets)
    graph.add_node("render_pdf", render_with_playwright)
    graph.add_node("render_pptx", render_with_python_pptx)
    graph.add_node("quality_check", verify_output_quality)

    # 边定义（工作流）
    graph.set_entry_point("parse_document")
    graph.add_edge("parse_document", "link_content_assets")
    graph.add_edge("link_content_assets", "analyze_semantics")
    graph.add_edge("analyze_semantics", "plan_layout")

    # 条件分支：素材不足时补充
    graph.add_conditional_edges(
        "plan_layout",
        lambda state: "supplement" if state.get("missing_assets") else "render",
        {"supplement": "supplement_assets", "render": "render_pdf"}
    )
    graph.add_edge("supplement_assets", "render_pdf")

    # 输出格式选择
    graph.add_conditional_edges(
        "render_pdf",
        lambda state: "pptx" if state.get("output_format") == "pptx" else "check",
        {"pptx": "render_pptx", "check": "quality_check"}
    )
    graph.add_edge("render_pptx", "quality_check")
    graph.add_edge("quality_check", END)

    return graph.compile()
```

### 模块4：Instructor + 智谱 GLM-5（增强LLM调用）

**为什么加 Instructor**：
- Pydantic 强类型约束 LLM 输出，100%结构化
- 自动重试 + 验证，告别 JSON 解析失败
- 与 FastAPI 天然契合（都用 Pydantic）

```python
import instructor
from pydantic import BaseModel, Field
from openai import OpenAI

# 通过 OpenAI 兼容接口调用智谱
client = instructor.from_openai(
    OpenAI(
        api_key="用户的智谱Key",
        base_url="https://open.bigmodel.cn/api/paas/v4",
    )
)

class DocumentStructure(BaseModel):
    """文档结构分析结果 - Pydantic强类型"""
    document_type: str = Field(description="product_intro|company_profile|marketing|technical_doc")
    target_audience: str = Field(description="目标受众")
    key_sections: list[KeySection] = Field(description="章节列表")
    highlights: list[str] = Field(description="需要重点突出的原文引用")
    suggested_pages: int = Field(description="建议总页数")

class KeySection(BaseModel):
    section_id: str
    title: str = Field(description="从原文提取的标题")
    key_points: list[str] = Field(description="从原文提取的关键信息")
    importance: Literal["high", "medium", "low"]
    suggested_pages: int

# 一行调用，100%结构化输出
structure = client.chat.completions.create(
    model="glm-5-pro",
    response_model=DocumentStructure,
    messages=[
        {"role": "system", "content": "你是专业商业文档分析师。所有分析必须100%基于原文。"},
        {"role": "user", "content": f"分析以下文档:\n{text_content}"},
    ],
    temperature=0.1,
)
# structure 已经是 DocumentStructure 实例，无需手动解析 JSON
```

### 模块5：智能素材补充系统（多源融合）

```python
class AssetSupplementer:
    """多源素材补充 - 搜索优先，生图兜底"""

    def __init__(self, session_id: str):
        self.unsplash = UnsplashAPI()    # 200万+ 高质量图片
        self.pexels = PexelsAPI()        # 免费商用
        self.pixabay = PixabayAPI()      # 610万+ CC0图片
        self.rembg = rembg               # 背景移除
        self.replicate = ReplicateAPI()  # FLUX.1 生图

    async def supplement(self, text_content: str, style: str) -> dict:
        """为文字内容寻找或生成配图"""

        # Step 1: 智谱生成精确搜索关键词
        keywords = await self.generate_keywords(text_content)

        # Step 2: 按优先级搜索免费素材
        for source in [self.unsplash, self.pexels, self.pixabay]:
            results = await source.search(keywords, per_page=5)
            if results:
                best = await self.select_best(results, text_content)
                # Step 3: 去背景 + 智能裁剪
                processed = await self.process_image(best["url"], style)
                return {"source": "search", "image": processed, "attribution": best["credit"]}

        # Step 4: 搜索不到 → AI 生图
        prompt = await self.generate_image_prompt(text_content, style)
        generated = await self.replicate.run("black-forest-labs/flux-schnell", {"prompt": prompt})
        processed = await self.process_image(generated["url"], style)
        return {"source": "generated", "image": processed}

    async def process_image(self, url: str, style: str) -> bytes:
        """背景移除 + 智能裁剪 + 色调调整"""
        img = await download(url)
        if style == "transparent":
            img = rembg.remove(img)
        img = smart_crop(img, target_ratio=(16/9))
        return img
```

### 模块6：质量校验系统（新增）

```python
class QualityChecker:
    """输出质量校验 - 确保忠于原意"""

    async def check(self, state: DocumentState) -> DocumentState:
        checks = {
            "content_completeness": self._check_all_content_preserved(state),
            "image_text_linkage": self._check_linkage_integrity(state),
            "layout_quality": self._check_layout_rules(state),
        }
        state["quality_score"] = sum(checks.values()) / len(checks)
        state["needs_review"] = state["quality_score"] < 0.85
        return state

    def _check_all_content_preserved(self, state) -> float:
        """校验所有原始内容是否都被包含在输出中"""
        original_texts = {e["id"]: e["content"] for e in state["parsed_elements"] if e["type"] == "text"}
        output_texts = set()  # 从生成的PDF/PPTX中提取
        coverage = len(output_texts & set(original_texts.values())) / len(original_texts)
        return coverage

    def _check_linkage_integrity(self, state) -> float:
        """校验图片-文字对应关系是否保持"""
        preserved = sum(1 for link in state["image_text_linkage"]
                       if link["image_id"] in output_images and link["text_id"] in output_texts)
        return preserved / max(len(state["image_text_linkage"]), 1)
```

---

## 四、开源组件清单

| 组件 | 项目 | Star | 协议 | 用途 |
|------|------|------|------|------|
| **Docling** | docling-project/docling | 7.3k+ | MIT | 统一文档解析 |
| **LangGraph** | langchain-ai/langgraph | 31.5k+ | MIT | 工作流编排 |
| **Instructor** | jxnl/instructor | 6k+ | MIT | LLM结构化输出 |
| **Playwright** | microsoft/playwright | 70k+ | Apache-2.0 | PDF渲染 |
| **Paged.js** | pagedjs/pagedjs | 1k+ | MIT | CSS分页控制 |
| **python-pptx** | scanny/python-pptx | 2.2k+ | MIT | PPTX生成 |
| **rembg** | danielgatis/rembg | 18k+ | MIT | 背景移除 |
| **FastAPI** | fastapi/fastapi | 80k+ | MIT | 后端API |
| **Next.js** | vercel/next.js | 130k+ | MIT | 前端UI |
| **Zustand** | pmndrs/zustand | 50k+ | MIT | 状态管理 |
| **MinIO** | minio/minio | 52k+ | AGPL-3.0 | 文件存储 |
| **Chroma** | chroma-core/chroma | 18k+ | Apache-2.0 | 向量数据库 |

**全部 MIT 或 Apache-2.0 协议，可自由商用**（MinIO 除外，用 Docker 部署即可）。

---

## 五、Docker Compose（6个容器，比V1减少40%）

```yaml
services:
  # 前端
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  # 后端（含 Docling + LangGraph + Playwright）
  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/output:/app/output
    depends_on: [redis, minio]

  # Redis（API Key 会话 + 任务队列）
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  # MinIO（文件存储）
  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"

  # Nginx（统一入口）
  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: [./nginx/nginx.conf:/etc/nginx/nginx.conf:ro]
```

> 去掉了：Dify API + Dify Web + Dify Worker + Dify PostgreSQL + Unstructured = **5个容器**
> 后端 Dockerfile 自带 Playwright + Docling，无需独立容器。

---

## 六、硬件要求（最低配置）

| 配置 | 最低要求 | 说明 |
|------|---------|------|
| CPU | 4核 | 8核更佳（并行渲染） |
| 内存 | **4GB** | 无本地模型，Redis+Playwright+FastAPI |
| 存储 | 50GB SSD | 文件缓存 + Docker镜像 |
| GPU | **不需要** | 所有AI通过API调用 |

> V1 需要 8GB 跑本地 BGE-m3 + PaddleOCR。V2 全部通过 API 调用，内存减半。

---

## 七、成本估算（用户自付）

| 服务 | 月成本（100份文档） | 说明 |
|------|---------------------|------|
| 智谱 GLM-5 Pro | ~30-50元 | 语义分析+排版规划 |
| Replicate (FLUX) | ~10-20元 | 仅搜索不到素材时生图 |
| 云服务器 4核4GB | ~80元/月 | 比 V1 降一档 |
| **总计** | **~120-150元/月** | **比 V1 节省 40%** |

> Unsplash/Pexels/Pixabay 素材搜索全部免费。

---

## 八、开发计划（6周，比V1缩短2周）

### 第1周：基础框架 + Docling 解析
- 搭建 FastAPI + Next.js 项目骨架
- 集成 Docling，实现 PPTX/PDF/Word/Excel 统一解析
- 实现图片-文字关联算法（三重策略）
- 实现 API Key 安全管理

### 第2周：LangGraph 工作流 + 智谱集成
- 构建 LangGraph 状态图（解析→关联→分析→排版→生成）
- 集成 Instructor + 智谱 GLM-5（结构化输出）
- 实现语义分析节点和排版规划节点
- 实现质量校验节点

### 第3周：PDF/PPTX 生成引擎
- 构建 HTML/CSS 杂志模板库（5套基础模板）
- 集成 Playwright + Paged.js 渲染管线
- 实现 python-pptx 生成管线
- 实现模板动态填充

### 第4周：素材补充系统
- 集成 Unsplash + Pexels + Pixabay 搜索
- 集成 Replicate FLUX.1 生图
- 集成 rembg 背景移除
- 实现多源融合策略

### 第5周：前端界面
- 文件上传 + 解析进度可视化
- 排版模板选择 + 实时预览
- 内容编辑 + 素材管理
- 导出控制面板

### 第6周：测试 + 优化 + 发布
- 50份不同类型文档全面测试
- 排版质量优化
- 性能调优
- Docker 镜像打包发布

---

## 九、风险与应对

| 风险 | 应对 |
|------|------|
| Docling 对某些格式解析不准 | 保留 PyMuPDF/python-pptx 作为降级方案 |
| Playwright 内存泄漏 | 实现 browser pool 管理，定期重启 |
| 智谱 API 不可用 | 预留 OpenAI/DeepSeek 接口一键切换 |
| 模板不够美观 | 模板 = HTML 文件，可随时找设计师补充 |

---

## 十、核心优势总结

1. **零GPU、低内存（4GB）、低成本（120元/月）**
2. **统一解析引擎（Docling），告别多解析器拼接**
3. **HTML/CSS 模板，任何前端开发者都能做杂志**
4. **Playwright 3ms/页渲染，比 Typst/WeasyPrint 快 75倍**
5. **LangGraph 纯Python编排，去掉 Dify 的 5个容器**
6. **Instructor 100%结构化输出，告别 JSON 解析失败**
7. **免费素材库（Unsplash/Pexels）+ AI生图兜底**
8. **全部 MIT/Apache 协议，可自由商用**
