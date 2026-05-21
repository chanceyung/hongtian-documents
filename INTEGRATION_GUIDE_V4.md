# 杂志级文档重构智能体 V4 — 多项目集成实施指南

> 本文档是开发者的操作手册：如何把 Presenton + PPTAgent + PPT Master 三个开源项目
> 集成为一个完整的多智能体系统，每个文件改什么、每个接口怎么对接。

---

## 一、集成架构总览（数据流视角）

```
用户上传文件 ─────────────────────────────────────────────────────────
    │                                                                │
    ▼                                                                │
┌─ Presenton 前端 (端口3000) ────────────────────────────────────────┐
│  已有: 文件上传组件 / 模板选择器 / 幻灯片预览器                     │
│  改造: 增加"文档美化"入口 / 保真报告页 / 素材补充面板               │
└────────────────────────┬───────────────────────────────────────────┘
                         │ POST /api/v1/magazine/generate
                         ▼
┌─ Presenton FastAPI 后端 (端口8000) ──────────────────────────────┐
│                                                                   │
│  ┌─ 新增路由: magazine_router.py ──────────────────────────────┐ │
│  │  POST /api/v1/magazine/upload      → 上传+解析             │ │
│  │  GET  /api/v1/magazine/status/{id} → 查询进度              │ │
│  │  POST /api/v1/magazine/generate     → 生成杂志版            │ │
│  │  GET  /api/v1/magazine/fidelity/{id}→ 保真报告              │ │
│  │  POST /api/v1/magazine/supplement   → 补充素材              │ │
│  │  GET  /api/v1/magazine/export/{id}  → 下载输出              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                         │                                         │
│  ┌─ LangGraph 工作流引擎 ──────────────────────────────────────┐ │
│  │                                                              │ │
│  │  [Parser Agent] ──→ [Analyzer Agent] ──→ [Designer Agent]   │ │
│  │       │                  │                      │            │ │
│  │       ▼                  ▼                      ▼            │ │
│  │  统一文档模型       PPTAgent风格分析        编辑动作生成      │ │
│  │  UnifiedDoc         内容聚类+模式提取       replace_only     │ │
│  │                                                              │ │
│  │  ──→ [Supplementer Agent] ──→ [Renderer Agent] ──→ [Fidelity]│ │
│  │           │                        │                  │      │ │
│  │           ▼                        ▼                  ▼      │ │
│  │      素材搜索/生图          PDF: Playwright+WeasyPrint  校验  │ │
│  │                             PPTX: PPT Master转换        │    │ │
│  │                                                  不通过→修复 │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌─ 共享数据层 ────────────────────────────────────────────────┐ │
│  │  SQLite/PostgreSQL: 任务状态、解析结果、生成记录              │ │
│  │  Redis: API Key 会话、任务队列、实时进度                      │ │
│  │  MinIO/本地文件: 上传文件、提取素材、生成输出                 │ │
│  └──────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

---

## 二、统一数据模型（三个项目之间的"通用语言"）

这是集成的关键——三个项目用不同的数据格式，需要定义一个中间层。

### 2.1 统一文档模型 (UnifiedDocument)

```python
# backend/app/models/unified_document.py
"""所有解析器输出此格式，所有下游模块消费此格式"""

from pydantic import BaseModel
from typing import Literal


class BoundingBox(BaseModel):
    """统一坐标格式（EMU单位，与PPTX一致）"""
    left: int    # EMU
    top: int     # EMU
    width: int   # EMU
    height: int  # EMU


class TextElement(BaseModel):
    id: str                          # 全局唯一ID
    content: str                     # 原始文字内容（不改一个字）
    page: int                        # 页码/幻灯片编号(0-based)
    bbox: BoundingBox | None = None  # 位置坐标
    level: int = 0                   # 标题级别(0=正文, 1=一级标题, 2=二级...)
    style: str = "Normal"            # 原始样式名
    fingerprint: str = ""            # MD5(content) 用于保真校验


class ImageElement(BaseModel):
    id: str
    local_path: str                  # 提取后的本地文件路径
    page: int
    bbox: BoundingBox | None = None
    width: int = 0                   # 原始像素宽度
    height: int = 0                  # 原始像素高度
    hash: str = ""                   # 文件MD5，用于完整性校验
    alt_text: str = ""               # 图片描述（如果有）


class TableElement(BaseModel):
    id: str
    page: int
    bbox: BoundingBox | None = None
    data: list[list[str]]            # 二维数组
    headers: list[str] = []          # 表头（如果有）
    is_chart: bool = False           # 是否是从图表提取的


class ContentAssetLink(BaseModel):
    """图片-文字关联关系"""
    text_id: str
    asset_id: str                    # 可以是 image_id 或 table_id
    asset_type: Literal["image", "table"]
    strategy: str                    # spatial | structural | semantic
    confidence: float                # 0-1，<0.6 标记需人工确认


class ContentFingerprint(BaseModel):
    """内容指纹——用于保真校验"""
    text_fingerprints: dict[str, str]   # {text_id: md5}
    image_hashes: dict[str, str]        # {image_id: md5}
    text_count: int
    image_count: int
    table_count: int
    total_chars: int


class UnifiedDocument(BaseModel):
    """统一文档模型——所有模块的数据交换格式"""
    source_file: str                     # 原始文件路径
    source_format: str                   # pptx | pdf | docx | xlsx | md
    title: str = ""                      # 文档标题（从内容提取）

    texts: list[TextElement] = []
    images: list[ImageElement] = []
    tables: list[TableElement] = []
    linkage: list[ContentAssetLink] = []

    # 元信息
    total_pages: int = 0
    parse_method: str = ""               # 使用了哪个解析器
    parse_warnings: list[str] = []       # 解析过程中的警告

    def compute_fingerprint(self) -> ContentFingerprint:
        """计算内容指纹"""
        import hashlib
        return ContentFingerprint(
            text_fingerprints={
                t.id: hashlib.md5(t.content.encode()).hexdigest()
                for t in self.texts
            },
            image_hashes={img.id: img.hash for img in self.images},
            text_count=len(self.texts),
            image_count=len(self.images),
            table_count=len(self.tables),
            total_chars=sum(len(t.content) for t in self.texts),
        )
```

### 2.2 编辑动作模型（来自 PPTAgent 概念）

```python
# backend/app/models/edit_actions.py
"""PPTAgent 风格的编辑动作——只替换，不重写"""

from pydantic import BaseModel
from typing import Literal


class EditAction(BaseModel):
    """单个编辑动作"""
    type: Literal["replace_text", "replace_image", "replace_table_data"]
    target_selector: str   # CSS选择器或占位符名称
    source_id: str         # UnifiedDocument 中的元素ID
    content: str | None = None   # 替换的内容（原文）
    confidence: float = 1.0


class SlideEditPlan(BaseModel):
    """单页编辑计划"""
    page_number: int                    # 目标页码(1-based)
    template_page: str                  # 模板中的页面标识
    actions: list[EditAction] = []      # 编辑动作列表
    notes: str = ""                     # 设计备注


class MagazineEditPlan(BaseModel):
    """完整杂志排版编辑计划"""
    document_id: str
    template_id: str                    # 选用的模板ID
    pages: list[SlideEditPlan] = []
    design_spec: dict = {}              # PPT Master 风格的设计规范
    original_fingerprint: dict = {}     # 原文指纹（用于校验）
```

### 2.3 设计规范模型（来自 PPT Master 概念）

```python
# backend/app/models/design_spec.py
"""PPT Master 风格的设计规范"""

from pydantic import BaseModel


class ColorScheme(BaseModel):
    primary: str     # "#2E86AB"
    secondary: str   # "#F24236"
    accent: str      # "#A23B72"
    background: str  # "#FAFAFA"
    text: str        # "#333333"
    muted: str       # "#888888"


class Typography(BaseModel):
    title_font: str = "Arial"
    body_font: str = "Arial"
    title_size: int = 48
    subtitle_size: int = 32
    body_size: int = 24
    caption_size: int = 18


class DesignSpec(BaseModel):
    """PPT Master 风格的设计规范 spec_lock"""
    canvas_format: str = "ppt169"       # ppt169 | a4 | a4_landscape
    canvas_width: int = 1920
    canvas_height: int = 1080
    colors: ColorScheme
    typography: Typography
    icon_library: str = "tabler-filled"
    target_pages: int = 10
    style: str = "modern_professional"   # 设计风格
```

---

## 三、五个智能体的职责和接口

### Agent 1: Parser Agent（文档解析智能体）

```python
# backend/app/agents/parser_agent.py
"""负责：文件类型路由 → 调用对应解析器 → 输出 UnifiedDocument"""

from app.models.unified_document import UnifiedDocument
from pathlib import Path


class ParserAgent:
    """按文件类型选择最佳解析器，输出统一格式"""

    async def parse(self, file_path: Path, session_id: str) -> UnifiedDocument:
        ext = file_path.suffix.lower()

        parsers = {
            ".pptx": self._parse_pptx,
            ".pdf":  self._parse_pdf,
            ".docx": self._parse_docx,
            ".xlsx": self._parse_xlsx,
            ".md":   self._parse_md,
        }

        parser = parsers.get(ext)
        if not parser:
            raise ValueError(f"不支持的格式: {ext}")

        doc = await parser(file_path)

        # 构建图文关联
        doc.linkage = self._build_linkage(doc)

        # 记录解析方法
        doc.parse_method = ext
        doc.source_format = ext.lstrip(".")

        return doc

    async def _parse_pptx(self, path: Path) -> UnifiedDocument:
        """PPTX: python-pptx 直接解析（最稳定）"""
        from pptx import Presentation
        from pptx.util import Emu
        import hashlib

        prs = Presentation(str(path))
        doc = UnifiedDocument(source_file=str(path), total_pages=len(prs.slides))

        for slide_idx, slide in enumerate(prs.slides):
            for shape in slide.shapes:
                # 文字
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if text:
                            doc.texts.append(TextElement(
                                id=f"s{slide_idx}_{shape.shape_id}_p{len(doc.texts)}",
                                content=text,
                                page=slide_idx,
                                bbox=BoundingBox(
                                    left=shape.left, top=shape.top,
                                    width=shape.width, height=shape.height,
                                ),
                                level=para.level,
                                fingerprint=hashlib.md5(text.encode()).hexdigest(),
                            ))

                # 图片
                if shape.shape_type == 13:
                    try:
                        img_bytes = shape.image.blob
                        ext = shape.image.content_type.split("/")[-1]
                        img_hash = hashlib.md5(img_bytes).hexdigest()[:12]
                        img_path = path.parent / "assets" / f"s{slide_idx}_{img_hash}.{ext}"
                        img_path.parent.mkdir(exist_ok=True)
                        img_path.write_bytes(img_bytes)

                        doc.images.append(ImageElement(
                            id=f"s{slide_idx}_img_{img_hash}",
                            local_path=str(img_path),
                            page=slide_idx,
                            bbox=BoundingBox(
                                left=shape.left, top=shape.top,
                                width=shape.width, height=shape.height,
                            ),
                            hash=img_hash,
                        ))
                    except Exception:
                        doc.parse_warnings.append(
                            f"Slide {slide_idx}: 图片提取失败 shape={shape.shape_id}"
                        )

                # 表格
                if shape.has_table:
                    data = [[cell.text for cell in row.cells]
                            for row in shape.table.rows]
                    doc.tables.append(TableElement(
                        id=f"s{slide_idx}_tbl_{shape.shape_id}",
                        page=slide_idx,
                        bbox=BoundingBox(
                            left=shape.left, top=shape.top,
                            width=shape.width, height=shape.height,
                        ),
                        data=data,
                        headers=data[0] if data else [],
                    ))

        return doc

    async def _parse_pdf(self, path: Path) -> UnifiedDocument:
        """PDF: Docling(子进程隔离) + PyMuPDF降级"""
        try:
            return await self._parse_pdf_docling(path)
        except Exception:
            doc.parse_warnings.append("Docling 失败，降级到 PyMuPDF")
            return await self._parse_pdf_pymupdf(path)

    # ... _parse_docx, _parse_xlsx, _parse_md 实现

    def _build_linkage(self, doc: UnifiedDocument) -> list[ContentAssetLink]:
        """三重策略构建图文关联"""
        links = []

        for text in doc.texts:
            for img in doc.images:
                if text.page != img.page:
                    continue

                # 策略1: 空间距离
                if text.bbox and img.bbox:
                    dist = self._bbox_distance(text.bbox, img.bbox)
                    if dist < 500000:  # EMU 距离阈值
                        links.append(ContentAssetLink(
                            text_id=text.id,
                            asset_id=img.id,
                            asset_type="image",
                            strategy="spatial",
                            confidence=max(0, 1 - dist / 500000),
                        ))

                # 策略2: 结构关键词
                content = text.content
                if any(kw in content for kw in ["图", "注", "见图", "如图", "图片"]):
                    if text.page == img.page:
                        links.append(ContentAssetLink(
                            text_id=text.id,
                            asset_id=img.id,
                            asset_type="image",
                            strategy="structural",
                            confidence=0.7,
                        ))

        # 策略3: 语义关联（调用智谱 API）
        # 由 Analyzer Agent 补充

        return links

    @staticmethod
    def _bbox_distance(a: BoundingBox, b: BoundingBox) -> float:
        import math
        ca = (a.left + a.width/2, a.top + a.height/2)
        cb = (b.left + b.width/2, b.top + b.height/2)
        return math.sqrt((ca[0]-cb[0])**2 + (ca[1]-cb[1])**2)
```

### Agent 2: Analyzer Agent（文档分析智能体）

```python
# backend/app/agents/analyzer_agent.py
"""PPTAgent 风格的文档分析：聚类 + 模式提取 + 语义关联"""

import instructor
from openai import AsyncOpenAI
from app.models.unified_document import UnifiedDocument, ContentAssetLink


class AnalyzerAgent:
    """阶段I: 分析文档结构（PPTAgent的Analysis阶段）"""

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4"):
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )

    async def analyze(self, doc: UnifiedDocument) -> dict:
        """完整分析流程"""

        # Step 1: 内容聚类（PPTAgent的Slide Clustering）
        groups = await self._cluster_content(doc)

        # Step 2: 模式提取（PPTAgent的Schema Extraction）
        patterns = await self._extract_patterns(doc, groups)

        # Step 3: 语义关联补充（用API替代本地BGE-m3）
        semantic_links = await self._semantic_linkage(doc)

        return {
            "content_groups": groups,
            "layout_patterns": patterns,
            "semantic_links": semantic_links,
            "document_type": patterns.get("document_type", "general"),
            "suggested_pages": patterns.get("suggested_pages", 10),
        }

    async def _cluster_content(self, doc: UnifiedDocument) -> list[dict]:
        """内容聚类——按主题/页面将内容分组"""

        class ContentGroup(BaseModel):
            group_id: str
            theme: str
            text_ids: list[str]
            image_ids: list[str]
            table_ids: list[str]
            suggested_layout: str  # cover | text_image | text_table | data_card | two_column

        class ClusteringResult(BaseModel):
            groups: list[ContentGroup]

        # 构建内容摘要（不发送原文，只发送结构和摘要）
        content_summary = []
        for t in doc.texts[:50]:  # 限制数量
            content_summary.append({
                "id": t.id, "page": t.page,
                "preview": t.content[:100], "level": t.level,
            })

        result = await self.client.chat.completions.create(
            model="glm-5-pro",
            response_model=ClusteringResult,
            messages=[
                {"role": "system", "content": "你是文档结构分析专家。将文档内容按主题分组。"},
                {"role": "user", "content": f"分析以下文档内容结构:\n{content_summary}"},
            ],
            temperature=0.1,
        )
        return [g.dict() for g in result.groups]

    async def _extract_patterns(self, doc: UnifiedDocument, groups: list) -> dict:
        """模式提取——识别文档类型和排版建议"""

        class PatternResult(BaseModel):
            document_type: str
            target_audience: str
            key_sections: list[dict]
            highlights: list[str]
            suggested_pages: int
            suggested_style: str

        text_for_analysis = "\n".join(
            t.content for t in doc.texts[:100]
        )[:8000]  # 控制长度

        result = await self.client.chat.completions.create(
            model="glm-5-pro",
            response_model=PatternResult,
            messages=[
                {"role": "system", "content": """分析文档内容，识别文档类型和结构。
规则：只基于提供的文本，不添加信息。"""},
                {"role": "user", "content": text_for_analysis},
            ],
            temperature=0.1,
        )
        return result.dict()

    async def _semantic_linkage(self, doc: UnifiedDocument) -> list[dict]:
        """语义关联——用GLM-5替代本地BGE-m3"""

        class SemanticLink(BaseModel):
            text_id: str
            image_id: str
            reason: str
            confidence: float

        class SemanticLinkResult(BaseModel):
            links: list[SemanticLink]

        # 只对没有空间/结构关联的文字寻找图片
        linked_text_ids = {l.text_id for l in doc.linkage}
        unlinked_texts = [t for t in doc.texts if t.id not in linked_text_ids]

        if not unlinked_texts or not doc.images:
            return []

        # 构建匹配请求
        text_summaries = [
            {"id": t.id, "content": t.content[:200], "page": t.page}
            for t in unlinked_texts[:20]
        ]
        image_summaries = [
            {"id": img.id, "page": img.page, "alt": img.alt_text}
            for img in doc.images
        ]

        result = await self.client.chat.completions.create(
            model="glm-5-pro",
            response_model=SemanticLinkResult,
            messages=[
                {"role": "system", "content": """根据文字内容和图片位置，判断哪些文字和哪些图片有关联。
只匹配同页的元素，给出置信度。"""},
                {"role": "user", "content": f"文字: {text_summaries}\n图片: {image_summaries}"},
            ],
            temperature=0.1,
        )
        return [l.dict() for l in result.links]
```

### Agent 3: Designer Agent（排版设计智能体）

```python
# backend/app/agents/designer_agent.py
"""PPTAgent 风格的排版规划：选择模板 + 生成编辑动作"""

import instructor
from openai import AsyncOpenAI
from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan, SlideEditPlan, EditAction
from app.models.design_spec import DesignSpec


class DesignerAgent:
    """阶段II: 基于编辑的排版设计（PPTAgent的Generation阶段）"""

    def __init__(self, api_key: str, base_url: str = "https://open.bigmodel.cn/api/paas/v4"):
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )

    async def design(
        self,
        doc: UnifiedDocument,
        analysis: dict,
        template_id: str,
    ) -> MagazineEditPlan:
        """完整的排版设计流程"""

        # Step 1: 确定设计规范（PPT Master 的 Strategist 角色）
        design_spec = await self._determine_design_spec(doc, analysis)

        # Step 2: 内容到页面分配
        page_mapping = await self._map_content_to_pages(doc, analysis, design_spec)

        # Step 3: 生成编辑动作（PPTAgent 的核心——只 replace，不 generate）
        edit_plan = await self._generate_edit_actions(doc, page_mapping, design_spec)

        # Step 4: 校验（确保所有原始内容都被包含）
        edit_plan = self._validate_completeness(doc, edit_plan)

        return edit_plan

    async def _determine_design_spec(self, doc, analysis) -> DesignSpec:
        """确定设计规范——颜色、字体、风格"""

        class DesignSpecResult(BaseModel):
            style: str
            color_primary: str
            color_secondary: str
            color_accent: str
            color_background: str
            suggested_pages: int

        result = await self.client.chat.completions.create(
            model="glm-5-pro",
            response_model=DesignSpecResult,
            messages=[
                {"role": "system", "content": "根据文档类型推荐设计规范。"},
                {"role": "user", "content": f"文档类型: {analysis.get('document_type')}\n目标受众: {analysis.get('target_audience')}"},
            ],
        )

        return DesignSpec(
            colors=ColorScheme(
                primary=result.color_primary,
                secondary=result.color_secondary,
                accent=result.color_accent,
                background=result.color_background,
            ),
            target_pages=result.suggested_pages,
            style=result.style,
        )

    async def _generate_edit_actions(
        self,
        doc: UnifiedDocument,
        page_mapping: list[dict],
        spec: DesignSpec,
    ) -> MagazineEditPlan:
        """★ 核心方法：生成编辑动作（只替换，不重写）"""

        pages = []

        for page_info in page_mapping:
            # 获取本页关联的文字、图片、表格
            page_texts = [t for t in doc.texts if t.id in page_info.get("text_ids", [])]
            page_images = [i for i in doc.images if i.id in page_info.get("image_ids", [])]
            page_tables = [t for t in doc.tables if t.id in page_info.get("table_ids", [])]

            actions = []

            # 为每个文字生成 replace 动作
            for text in page_texts:
                selector = self._get_selector_for_text(text, page_info["layout_type"])
                actions.append(EditAction(
                    type="replace_text",
                    target_selector=selector,
                    source_id=text.id,
                    content=text.content,  # ★ 原文直接赋值，不经LLM
                    confidence=1.0,
                ))

            # 为每个图片生成 replace 动作
            for img in page_images:
                selector = self._get_selector_for_image(img, page_info["layout_type"])
                actions.append(EditAction(
                    type="replace_image",
                    target_selector=selector,
                    source_id=img.id,
                    confidence=1.0,
                ))

            # 为每个表格生成 replace 动作
            for tbl in page_tables:
                selector = self._get_selector_for_table(tbl, page_info["layout_type"])
                actions.append(EditAction(
                    type="replace_table_data",
                    target_selector=selector,
                    source_id=tbl.id,
                    confidence=1.0,
                ))

            pages.append(SlideEditPlan(
                page_number=page_info["page_number"],
                template_page=page_info["layout_type"],
                actions=actions,
            ))

        return MagazineEditPlan(
            document_id=doc.source_file,
            template_id=spec.style,
            pages=pages,
            design_spec=spec.dict(),
            original_fingerprint=doc.compute_fingerprint().dict(),
        )

    def _validate_completeness(
        self, doc: UnifiedDocument, plan: MagazineEditPlan
    ) -> MagazineEditPlan:
        """校验所有原始内容是否都被包含在编辑计划中"""

        planned_text_ids = set()
        planned_image_ids = set()
        planned_table_ids = set()

        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_text":
                    planned_text_ids.add(action.source_id)
                elif action.type == "replace_image":
                    planned_image_ids.add(action.source_id)
                elif action.type == "replace_table_data":
                    planned_table_ids.add(action.source_id)

        # 检查遗漏
        missing_texts = [t.id for t in doc.texts if t.id not in planned_text_ids]
        missing_images = [i.id for i in doc.images if i.id not in planned_image_ids]

        if missing_texts or missing_images:
            # 自动追加遗漏内容到最后一个页面
            last_page = plan.pages[-1] if plan.pages else None
            if not last_page:
                last_page = SlideEditPlan(
                    page_number=len(plan.pages) + 1,
                    template_page="text_only",
                )
                plan.pages.append(last_page)

            for text_id in missing_texts:
                text = next(t for t in doc.texts if t.id == text_id)
                last_page.actions.append(EditAction(
                    type="replace_text",
                    target_selector=f".extra-text-{len(last_page.actions)}",
                    source_id=text_id,
                    content=text.content,
                ))

            for img_id in missing_images:
                last_page.actions.append(EditAction(
                    type="replace_image",
                    target_selector=f".extra-image-{len(last_page.actions)}",
                    source_id=img_id,
                ))

        return plan
```

### Agent 4: Renderer Agent（渲染智能体）

```python
# backend/app/agents/renderer_agent.py
"""双轨渲染：PDF路径 + PPTX路径"""

from app.models.edit_actions import MagazineEditPlan
from app.models.unified_document import UnifiedDocument


class RendererAgent:
    """根据输出格式选择渲染引擎"""

    async def render_pdf(
        self, plan: MagazineEditPlan, doc: UnifiedDocument, template_dir: Path
    ) -> Path:
        """PDF 路径: HTML模板填充 → 混合引擎渲染"""

        # 1. 加载 HTML/CSS 模板
        template_path = template_dir / plan.template_id / "template.html"
        template_html = template_path.read_text(encoding="utf-8")

        # 2. 填充编辑动作到模板
        filled_html = self._apply_edit_actions_html(template_html, plan, doc)

        # 3. 按页面类型选择渲染引擎
        pdf_pages = []
        for page in plan.pages:
            page_html = self._extract_page_html(filled_html, page.page_number)

            if page.template_page in ("cover", "hero", "data_card"):
                # 视觉复杂页 → Playwright
                pdf_bytes = await self._render_playwright(page_html)
            else:
                # 文字表格页 → WeasyPrint
                pdf_bytes = await self._render_weasyprint(page_html)

            pdf_pages.append(pdf_bytes)

        # 4. 合并所有页面
        from PyPDF2 import PdfMerger
        import io

        merger = PdfMerger()
        for pdf_bytes in pdf_pages:
            merger.append(io.BytesIO(pdf_bytes))

        output_path = Path(f"output/{plan.document_id}/magazine.pdf")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        merger.write(str(output_path))
        merger.close()

        return output_path

    async def render_pptx(
        self, plan: MagazineEditPlan, doc: UnifiedDocument, template_dir: Path
    ) -> Path:
        """PPTX 路径: PPT Master 模板 + SVG→DrawingML"""

        # 1. 使用 PPT Master 的模板提取
        # 从精美 PPTX 模板提取 SVG 骨架
        template_pptx = template_dir / plan.template_id / "template.pptx"

        # 2. 将编辑动作转换为 SVG 修改
        svg_pages = []
        for page in plan.pages:
            svg_template = self._load_svg_template(template_dir, plan.template_id, page)
            svg_filled = self._apply_edit_actions_svg(svg_template, page, doc)
            svg_pages.append(svg_filled)

        # 3. PPT Master 后处理
        # finalize_svg: embed-icons → crop-images → fix-aspect → embed-images → flatten-text
        finalized_svgs = self._finalize_svgs(svg_pages, plan.design_spec)

        # 4. PPT Master SVG→DrawingML 转换
        output_path = self._svg_to_pptx(finalized_svgs, plan.design_spec)

        return output_path

    def _apply_edit_actions_html(self, template: str, plan, doc) -> str:
        """将编辑动作应用到 HTML 模板"""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(template, "html.parser")

        for page in plan.pages:
            page_el = soup.select_one(f'[data-page="{page.page_number}"]')
            if not page_el:
                continue

            for action in page.actions:
                target = page_el.select_one(action.target_selector)
                if not target:
                    continue

                if action.type == "replace_text":
                    # ★ 直接替换为原文，不经过 LLM
                    target.string = action.content

                elif action.type == "replace_image":
                    img = doc.find_image(action.source_id)
                    if img:
                        target["src"] = img.local_path

                elif action.type == "replace_table_data":
                    tbl = doc.find_table(action.source_id)
                    if tbl:
                        # 重构表格 HTML
                        table_html = self._build_table_html(tbl.data, tbl.headers)
                        target.replace_with(BeautifulSoup(table_html, "html.parser"))

        return str(soup)

    def _apply_edit_actions_svg(self, svg_template: str, page, doc) -> str:
        """将编辑动作应用到 SVG 模板（PPT Master 格式）"""
        from bs4 import BeautifulSoup
        import base64

        soup = BeautifulSoup(svg_template, "xml")

        for action in page.actions:
            target = soup.select_one(action.target_selector)
            if not target:
                continue

            if action.type == "replace_text":
                # SVG 中替换 <text> 内容
                target.string = action.content

            elif action.type == "replace_image":
                img = doc.find_image(action.source_id)
                if img:
                    # PPT Master 要求 base64 内联图片
                    with open(img.local_path, "rb") as f:
                        img_b64 = base64.b64encode(f.read()).decode()
                    target["href"] = f"data:image/jpeg;base64,{img_b64}"

        return str(soup)
```

### Agent 5: Fidelity Agent（保真校验智能体）

```python
# backend/app/agents/fidelity_agent.py
"""四层保真校验——生成前后对比，不过95%不放行"""

# （沿用 V3 的 ContentFidelityPipeline 设计，此处不重复）
# 关键区别：语义对比用 GLM-5 API 而非本地模型
```

---

## 四、LangGraph 工作流编排

```python
# backend/app/workflow/magazine_pipeline.py
"""完整的 LangGraph 状态图——串联五个智能体"""

from langgraph.graph import StateGraph, END
from typing import TypedDict


class PipelineState(TypedDict):
    # 输入
    file_path: str
    session_id: str
    output_format: str       # "pdf" | "pptx"
    template_id: str

    # Parser Agent 输出
    document: UnifiedDocument
    parse_warnings: list[str]

    # Analyzer Agent 输出
    analysis: dict

    # Designer Agent 输出
    edit_plan: MagazineEditPlan
    design_spec: DesignSpec

    # Supplementer Agent 输出（按需）
    supplemented: bool

    # Renderer Agent 输出
    output_path: str

    # Fidelity Agent 输出
    fidelity_score: float
    fidelity_passed: bool
    fidelity_issues: list[dict]
    repair_count: int


def build_magazine_pipeline() -> CompiledGraph:
    graph = StateGraph(PipelineState)

    # 注册节点
    graph.add_node("parse", parser_node)
    graph.add_node("analyze", analyzer_node)
    graph.add_node("design", designer_node)
    graph.add_node("check_missing", check_missing_assets_node)
    graph.add_node("supplement", supplement_node)
    graph.add_node("render", renderer_node)
    graph.add_node("verify", fidelity_node)
    graph.add_node("repair", repair_node)
    graph.add_node("finalize", finalize_node)

    # 定义流程
    graph.set_entry_point("parse")
    graph.add_edge("parse", "analyze")
    graph.add_edge("analyze", "design")

    # 条件: 检查是否有缺失素材
    graph.add_conditional_edges(
        "design", check_missing_assets_node,
        {
            "supplement": "supplement",
            "render": "render",
        }
    )
    graph.add_edge("supplement", "render")
    graph.add_edge("render", "verify")

    # 条件: 保真校验通过？
    graph.add_conditional_edges(
        "verify",
        lambda s: "repair" if not s["fidelity_passed"] and s.get("repair_count", 0) < 2 else "finalize",
        {"repair": "repair", "finalize": "finalize"},
    )
    graph.add_edge("repair", "verify")
    graph.add_edge("finalize", END)

    return graph.compile()


# ---- 节点实现 ----

async def parser_node(state: PipelineState) -> PipelineState:
    agent = ParserAgent()
    doc = await agent.parse(Path(state["file_path"]), state["session_id"])
    state["document"] = doc
    state["parse_warnings"] = doc.parse_warnings
    return state


async def analyzer_node(state: PipelineState) -> PipelineState:
    api_key = await get_api_key(state["session_id"])
    agent = AnalyzerAgent(api_key)
    analysis = await agent.analyze(state["document"])
    state["analysis"] = analysis
    return state


async def designer_node(state: PipelineState) -> PipelineState:
    api_key = await get_api_key(state["session_id"])
    agent = DesignerAgent(api_key)
    plan = await agent.design(state["document"], state["analysis"], state["template_id"])
    state["edit_plan"] = plan
    state["design_spec"] = plan.design_spec
    return state


async def check_missing_assets_node(state: PipelineState) -> str:
    """检查编辑计划中是否有需要补充的素材"""
    plan = state["edit_plan"]
    doc = state["document"]
    for page in plan.pages:
        for action in page.actions:
            if action.type == "replace_image":
                img = next((i for i in doc.images if i.id == action.source_id), None)
                if not img or not Path(img.local_path).exists():
                    return "supplement"
    return "render"


async def supplement_node(state: PipelineState) -> PipelineState:
    """补充缺失素材"""
    from app.agents.supplement_agent import SupplementAgent
    agent = SupplementAgent(state["session_id"])
    await agent.supplement(state["document"], state["edit_plan"])
    state["supplemented"] = True
    return state


async def renderer_node(state: PipelineState) -> PipelineState:
    agent = RendererAgent()
    if state["output_format"] == "pdf":
        path = await agent.render_pdf(
            state["edit_plan"], state["document"],
            Path("templates/pdf/")
        )
    else:
        path = await agent.render_pptx(
            state["edit_plan"], state["document"],
            Path("templates/pptx/")
        )
    state["output_path"] = str(path)
    return state


async def fidelity_node(state: PipelineState) -> PipelineState:
    from app.agents.fidelity_agent import FidelityAgent
    api_key = await get_api_key(state["session_id"])
    agent = FidelityAgent(api_key)
    result = await agent.verify(state["document"], state["edit_plan"])
    state["fidelity_score"] = result.overall_score
    state["fidelity_passed"] = result.passed
    state["fidelity_issues"] = result.issues
    return state


async def repair_node(state: PipelineState) -> PipelineState:
    """自动修复——将遗漏内容追加到编辑计划"""
    state["repair_count"] = state.get("repair_count", 0) + 1
    for issue in state.get("fidelity_issues", []):
        if issue["type"] == "missing_text":
            # 追加到编辑计划
            ...
    return state
```

---

## 五、Presenton 集成改造清单

### 5.1 后端改造（Presenton 已有的基础上）

```
Presenton 后端原有结构:
backend/
├── app/
│   ├── main.py                 # 保留
│   ├── api/
│   │   ├── deps.py             # 保留
│   │   └── v1/
│   │       ├── auth.py         # 保留
│   │       └── ppt.py          # 保留（原有PPT生成功能）
│   ├── models/                 # 保留（SQLAlchemy模型）
│   ├── services/               # 保留（LLM调用等）
│   └── core/                   # 保留（配置等）
│
│   ★ 新增目录:
│   ├── agents/                 # 五个智能体
│   │   ├── parser_agent.py
│   │   ├── analyzer_agent.py
│   │   ├── designer_agent.py
│   │   ├── renderer_agent.py
│   │   ├── fidelity_agent.py
│   │   └── supplement_agent.py
│   ├── models/                 # ★ 新增统一数据模型
│   │   ├── unified_document.py
│   │   ├── edit_actions.py
│   │   └── design_spec.py
│   ├── workflow/               # ★ 新增 LangGraph 工作流
│   │   └── magazine_pipeline.py
│   ├── exporters/              # ★ 新增导出引擎
│   │   ├── ppt_master/         # 从 PPT Master 集成的转换器
│   │   │   ├── svg_to_pptx.py
│   │   │   ├── finalize_svg.py
│   │   │   └── svg_quality_checker.py
│   │   ├── pdf_renderer.py     # 混合PDF引擎
│   │   └── weasyprint_renderer.py
│   ├── parsers/                # ★ 新增多格式解析器
│   │   ├── pptx_parser.py
│   │   ├── pdf_parser.py
│   │   ├── docx_parser.py
│   │   ├── xlsx_parser.py
│   │   └── md_parser.py
│   └── templates/              # ★ 新增杂志模板库
│       ├── pdf/                # HTML/CSS 模板
│       │   ├── modern_tech/
│       │   │   ├── template.html
│       │   │   └── config.json
│       │   ├── business_pro/
│       │   └── product_catalog/
│       └── pptx/               # PPTX 模板 + SVG 骨架
│           ├── modern_tech/
│           │   ├── template.pptx    # 设计师制作的精美PPTX
│           │   ├── page_1_cover.svg
│           │   ├── page_2_content.svg
│           │   └── config.json
│           ├── business_pro/
│           └── product_catalog/
```

### 5.2 新增 API 路由

```python
# backend/app/api/v1/magazine.py
"""杂志级文档重构 API —— 挂载到 Presenton 的 FastAPI"""

from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends

router = APIRouter(prefix="/magazine", tags=["Magazine"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks,
):
    """上传文件并启动解析"""
    task_id = await save_upload(file)
    background_tasks.add_task(run_parse_pipeline, task_id)
    return {"task_id": task_id, "status": "parsing"}


@router.get("/status/{task_id}")
async def get_status(task_id: str):
    """查询处理进度"""
    return await get_task_status(task_id)


@router.post("/generate")
async def generate_magazine(request: GenerateRequest):
    """启动杂志级生成"""
    task_id = await start_generation(request)
    return {"task_id": task_id}


@router.get("/fidelity/{task_id}")
async def get_fidelity_report(task_id: str):
    """获取保真校验报告"""
    return await get_fidelity(task_id)


@router.get("/export/{task_id}")
async def export_file(task_id: str, format: str = "pdf"):
    """下载生成结果"""
    file_path = await get_output_path(task_id, format)
    return FileResponse(file_path)
```

### 5.3 环境变量配置

```bash
# Presenton 原有（直接使用）
LLM=custom
CUSTOM_LLM_URL=https://open.bigmodel.cn/api/paas/v4
CUSTOM_MODEL=glm-5-pro
CUSTOM_LLM_API_KEY=${GLM_API_KEY}
IMAGE_PROVIDER=pexels
PEXELS_API_KEY=${PEXELS_KEY}
DATABASE_URL=sqlite:///./app_data/magazine.db

# ★ 新增
MAGAZINE_TEMPLATES_DIR=/app/app/templates
FIDELITY_THRESHOLD=0.95
MAX_REPAIR_ATTEMPTS=2
DOCILING_TIMEOUT=300
REPLICATE_API_TOKEN=${REPLICATE_KEY}
UNSPLASH_ACCESS_KEY=${UNSPLASH_KEY}
```

### 5.4 前端改造（Presenton 已有的基础上）

```
新增页面:
frontend/src/app/
├── import/                    # ★ 新增：多格式文档导入页
│   └── page.tsx               # 拖拽上传 + 格式识别 + 进度显示
├── magazine/                  # ★ 新增：杂志级重构流程
│   ├── [id]/analyze/page.tsx  # 文档分析结果页
│   ├── [id]/design/page.tsx   # 模板选择 + 设计调整
│   ├── [id]/preview/page.tsx  # 实时预览 + 保真报告
│   └── [id]/export/page.tsx   # 导出选项
└── ...

新增组件:
frontend/src/components/
├── FidelityReport/            # ★ 新增：保真度可视化
│   ├── ScoreGauge.tsx
│   ├── CheckItem.tsx
│   └── IssueCard.tsx
├── DocumentPreview/           # ★ 新增：原始文档预览
│   └── PdfViewer.tsx
├── TemplateGallery/           # 改造 Presenton 已有的模板选择器
│   └── MagazineTemplates.tsx
└── AssetSupplement/           # ★ 新增：素材补充面板
    └── SupplementPanel.tsx
```

---

## 六、PPT Master 集成的具体操作

### 6.1 复制核心转换器

```bash
# 从 PPT Master 提取需要的文件
git clone --depth 1 https://github.com/hugohe3/ppt-master.git /tmp/ppt-master

# 核心转换器
cp /tmp/ppt-master/skills/ppt-master/scripts/svg_to_pptx.py \
   backend/app/exporters/ppt_master/

cp /tmp/ppt-master/skills/ppt-master/scripts/finalize_svg.py \
   backend/app/exporters/ppt_master/

# SVG 后处理模块
cp -r /tmp/ppt-master/skills/ppt-master/scripts/svg_finalize/ \
   backend/app/exporters/ppt_master/svg_finalize/

# 图标库
cp -r /tmp/ppt-master/skills/ppt-master/templates/icons/ \
   backend/app/templates/pptx/icons/

# 质量检查器
cp /tmp/ppt-master/skills/ppt-master/scripts/svg_quality_checker.py \
   backend/app/exporters/ppt_master/

# 坐标计算器（用于图表）
cp /tmp/ppt-master/skills/ppt-master/scripts/svg_position_calculator.py \
   backend/app/exporters/ppt_master/
```

### 6.2 SVG 模板制作规范

PPT Master 对 SVG 有严格的要求，模板必须遵循：

```xml
<!-- ★ 合法的 SVG 模板示例（封面页） -->
<svg viewBox="0 0 1920 1080" width="1920" height="1080"
     xmlns="http://www.w3.org/2000/svg">

  <!-- 背景 -->
  <rect width="1920" height="1080" fill="#1a1a2e"/>

  <!-- 渐变装饰 -->
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f3460"/>
      <stop offset="100%" stop-color="#16213e"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="960" height="1080" fill="url(#grad1)"/>

  <!-- ★ 占位符：标题（Designer Agent 替换此处） -->
  <text x="120" y="420" font-family="Arial" font-size="56" font-weight="bold"
        fill="#ffffff" data-placeholder="title">
    【产品名称】
  </text>

  <!-- ★ 占位符：副标题 -->
  <text x="120" y="500" font-family="Arial" font-size="28"
        fill="#ffffff" fill-opacity="0.8" data-placeholder="subtitle">
    【产品描述】
  </text>

  <!-- ★ 占位符：封面图片 -->
  <image x="960" y="100" width="860" height="880"
         href="data:image/jpeg;base64,..." preserveAspectRatio="xMidYMid slice"
         data-placeholder="cover_image"/>

  <!-- 装饰元素（不会被替换） -->
  <circle cx="1800" cy="100" r="80" fill="#e94560" fill-opacity="0.3"/>
  <rect x="120" y="560" width="120" height="4" fill="#e94560"/>
</svg>
```

---

## 七、PPTAgent 集成的具体操作

### 7.1 不直接 Fork PPTAgent，而是移植核心算法

```bash
# PPTAgent 需要本地 72B 模型 + A100 GPU
# 我们的策略：移植算法思想，用 GLM-5 API 替代本地模型

# 需要参考的 PPTAgent 文件（阅读源码，不直接复制）:
# 1. deeppresenter/analyzer/ - 分析阶段的聚类和模式提取逻辑
# 2. deeppresenter/generator/ - 生成阶段的编辑动作格式
# 3. deeppresenter/self_correct/ - REPL 自我纠错机制
# 4. deeppresenter/config.yaml - 配置格式参考
```

### 7.2 编辑动作到 PPT Master SVG 的映射

```python
# PPTAgent 的 HTML 编辑动作 → PPT Master 的 SVG 元素
MAPPING = {
    # PPTAgent CSS 选择器          → PPT Master SVG 选择器
    ".slide-title":               "[data-placeholder='title']",
    ".slide-subtitle":            "[data-placeholder='subtitle']",
    ".slide-body":                "[data-placeholder='body']",
    ".slide-image":               "[data-placeholder='cover_image']",
    ".data-card-value":           "[data-placeholder='data_value']",
    ".data-card-label":           "[data-placeholder='data_label']",
    ".quote-text":                "[data-placeholder='quote']",
    ".table-container":           "[data-placeholder='table']",
}
```

---

## 八、开发执行顺序（5周，按天排）

### 第1周：基础搭建

| 天 | 任务 | 具体操作 |
|----|------|---------|
| 1 | Fork Presenton | `git clone` → 配置 `.env` → `docker-compose up` → 跑通 |
| 2 | 配置 GLM-5 | 设置 `CUSTOM_LLM_URL` → 测试 API 调用 → 确认生成可用 |
| 3 | 创建数据模型 | 写 `unified_document.py` + `edit_actions.py` + `design_spec.py` |
| 4 | 实现 Parser Agent | PPTX 解析器 → PDF 解析器 → DOCX/XLSX/MD 解析器 |
| 5 | 集成测试 | 上传各种格式文件 → 验证输出 UnifiedDocument → 测试图文关联 |

### 第2周：核心智能体

| 天 | 任务 | 具体操作 |
|----|------|---------|
| 6 | Analyzer Agent | 内容聚类 + 模式提取 + 语义关联（GLM-5） |
| 7 | Designer Agent | 设计规范确定 + 内容到页面分配 + 编辑动作生成 |
| 8 | LangGraph 工作流 | 构建状态图 → 串联 Parser → Analyzer → Designer |
| 9 | Fidelity Agent | 四层保真校验 + 自动修复 + 降级策略 |
| 10 | 端到端测试 | 上传PPTX → 解析 → 分析 → 设计 → 校验 → 通过 |

### 第3周：渲染引擎

| 天 | 任务 | 具体操作 |
|----|------|---------|
| 11 | PPT Master 集成 | 复制核心转换器 → 测试 SVG→DrawingML |
| 12 | 制作 3 套 PPTX 模板 | 按PPT Master SVG规范制作封面+内容+数据页模板 |
| 13 | 制作 3 套 PDF 模板 | HTML/CSS 模板（封面+正文+表格页） |
| 14 | Renderer Agent (PPTX) | SVG模板填充 → finalize → svg_to_pptx |
| 15 | Renderer Agent (PDF) | HTML模板填充 → WeasyPrint + Playwright 混合渲染 |

### 第4周：素材与前端

| 天 | 任务 | 具体操作 |
|----|------|---------|
| 16 | Supplement Agent | Unsplash/Pexels 搜索 → rembg → Replicate 生图 |
| 17 | Presenton 前端改造 | 导入页面 + 模板选择器 + 进度显示 |
| 18 | 保真报告页面 | 分数仪表盘 + 四层检查结果 + 问题列表 |
| 19 | 预览和导出 | PDF 预览 + PPTX 下载 + 调整控制 |
| 20 | 前后端联调 | 完整用户流程测试 |

### 第5周：测试和发布

| 天 | 任务 | 具体操作 |
|----|------|---------|
| 21 | 边界测试 | 大文件、扫描件PDF、复杂表格、多图PPTX、空文件 |
| 22 | 保真测试 | 50 份不同文档 → 每份检查四层校验结果 |
| 23 | 性能优化 | 并发控制、内存管理、缓存策略 |
| 24 | Docker 镜像 | 打包完整镜像 → 编写部署文档 |
| 25 | 发布 | 清理代码 → 写 README → 内测 |

---

## 九、模板制作指南（设计师协作）

### PDF 模板（HTML/CSS）

```
templates/pdf/
├── modern_tech/
│   ├── template.html      # 完整HTML模板（含所有页面类型）
│   ├── styles.css         # 排版样式
│   └── config.json        # 页面布局配置
└── business_pro/
    └── ...
```

`config.json` 格式：
```json
{
  "name": "现代科技风",
  "pages": [
    {
      "page_number": 1,
      "layout_type": "cover",
      "placeholders": {
        "title": {"selector": ".cover-title", "type": "text"},
        "subtitle": {"selector": ".cover-subtitle", "type": "text"},
        "cover_image": {"selector": ".cover-image", "type": "image"}
      }
    },
    {
      "page_number": 2,
      "layout_type": "text_with_image",
      "placeholders": {
        "heading": {"selector": ".section-title", "type": "text"},
        "body": {"selector": ".section-body", "type": "text"},
        "image": {"selector": ".section-image", "type": "image"}
      }
    }
  ],
  "colors": {
    "primary": "#0f3460",
    "accent": "#e94560",
    "background": "#ffffff"
  }
}
```

### PPTX 模板（SVG 骨架）

```
templates/pptx/
├── modern_tech/
│   ├── template.pptx              # 基础PPTX（用于提取主题）
│   ├── pages/
│   │   ├── cover.svg              # 封面页SVG骨架
│   │   ├── content_text.svg       # 纯文字页
│   │   ├── content_image_text.svg # 图文混排页
│   │   ├── data_card.svg          # 数据卡片页
│   │   └── table_page.svg         # 表格页
│   └── config.json                # 页面配置
└── business_pro/
    └── ...
```

---

## 十、最终交付物清单

### 代码仓库结构

```
doc-magazine-agent/                    # 基于 Presenton fork
├── docker-compose.yml                 # 一键启动
├── Dockerfile                         # 后端镜像
├── .env.example                       # 环境变量模板
├── backend/
│   ├── app/
│   │   ├── main.py                    # Presenton 原有
│   │   ├── api/v1/
│   │   │   ├── auth.py                # Presenton 原有
│   │   │   ├── ppt.py                 # Presenton 原有
│   │   │   └── magazine.py            # ★ 新增
│   │   ├── agents/                    # ★ 五个智能体
│   │   ├── models/                    # ★ 统一数据模型
│   │   ├── workflow/                  # ★ LangGraph 工作流
│   │   ├── exporters/                 # ★ 渲染引擎
│   │   │   ├── ppt_master/            # 从 PPT Master 集成
│   │   │   └── pdf_renderer.py
│   │   ├── parsers/                   # ★ 多格式解析器
│   │   └── templates/                 # ★ 杂志模板库
│   └── requirements.txt
├── frontend/                          # Presenton 原有 + 改造
│   └── src/
│       ├── app/magazine/              # ★ 新增页面
│       └── components/FidelityReport/ # ★ 新增组件
└── docs/
    ├── INTEGRATION.md                 # 集成指南
    └── TEMPLATE_GUIDE.md             # 模板制作指南
```
