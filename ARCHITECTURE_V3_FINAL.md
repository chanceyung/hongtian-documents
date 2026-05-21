# 杂志级文档重构智能体 V3 — 生产级最终方案

> 经过多轮深度审查，V2 方案中发现 5 个致命稳定性问题，本方案全部修正。
> 原则：**宁可多写一层兜底，也不允许输出不稳定。**

---

## 零、V2 致命问题及修正对照表

| # | 致命问题 | 影响程度 | V3 修正 |
|---|---------|---------|---------|
| 1 | Docling PPTX 解析丢失占位符图片、忽略图表 | **致命** | 按文件类型分管道，PPTX 用 python-pptx 直接解析 |
| 2 | Playwright 表格分页时 TR/TD 被 page-break 切断 | **致命** | 混合引擎：Playwright(视觉页) + WeasyPrint(文字表格页) |
| 3 | python-pptx 中文字体只能用宋体，无法嵌入 | **致命** | PPTX 改用"模板填充"模式，不从头生成 |
| 4 | LLM 可能悄悄改写/增删原文内容 | **致命** | 增加四层内容保真验证管线 |
| 5 | Docling 处理大文件内存泄漏至12GB | **高危** | 子进程隔离 + 内存限制 + 分块处理 |

---

## 一、系统架构（V3 最终版）

```
┌─────────────────────────────────────────────────────────────────────┐
│                         用户浏览器                                   │
│   Next.js 前端（上传 / 预览 / 模板选择 / 编辑 / 导出）              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    FastAPI 后端（单进程）                             │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────────┐ │
│  │              文件类型路由器（核心稳定性保障）                     │ │
│  │                                                                │ │
│  │   PDF  ──→  Docling 子进程(隔离)                               │ │
│  │   PPTX ──→  python-pptx 直接解析（不用Docling）                │ │
│  │   DOCX ──→  python-docx + Docling(辅助)                        │ │
│  │   XLSX ──→  pandas + openpyxl                                  │ │
│  │   MD   ──→  正则 + markdown-it-py                              │ │
│  │                                                                │ │
│  │   共同输出 → 统一结构化JSON（含坐标+图文关联）                  │ │
│  └────────────────────────────────────────────────────────────────┘ │
│                               │                                     │
│  ┌────────────────────────────┼────────────────────────────────┐   │
│  │         LangGraph 工作流引擎                                  │   │
│  │                                                              │   │
│  │  解析 → 关联 → 语义分析(智谱) → 排版规划(智谱)              │   │
│  │       → 素材补充 → 生成 → ★四层保真校验 → 输出              │   │
│  └────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│  ┌────────────────────────────┼────────────────────────────────┐   │
│  │              混合 PDF 生成引擎                                │   │
│  │                                                              │   │
│  │  视觉页（封面/数据卡片）→ Playwright 渲染                    │   │
│  │  文字表格页（正文/表格）  → WeasyPrint 渲染                  │   │
│  │  合并 → 最终 PDF                                             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│  ┌────────────────────────────┼────────────────────────────────┐   │
│  │              PPTX 模板填充引擎                                │   │
│  │                                                              │   │
│  │  精美PPTX模板(设计师制作) → python-pptx + pptx-ea-font       │   │
│  │  → 替换占位符文字和图片 → 输出可编辑PPTX                     │   │
│  └────────────────────────────────────────────────────────────┘   │
│                               │                                     │
│  ┌────────────────────────────┼────────────────────────────────┐   │
│  │           ★ 四层内容保真校验管线（核心新增）                   │   │
│  │                                                              │   │
│  │  第1层：内容指纹完整性校验（零遗漏）                         │   │
│  │  第2层：图文对应关系校验（零错位）                           │   │
│  │  第3层：语义保真校验（智谱API对比）                          │   │
│  │  第4层：人工确认机制（低置信度标记）                         │   │
│  └────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     基础设施（7个容器）                              │
│  Backend │ Frontend │ Redis │ MinIO │ Playwright │ WeasyPrint │ Nginx│
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│               用户自付 API（用户自填Key）                            │
│  智谱GLM-5 Pro（语义分析+保真校验）│ Unsplash/Pexels（素材搜索）   │
│  智谱GLM-5V（图片理解，可选）      │ Replicate（AI生图，按需）     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、致命问题修正详解

### 修正1：按文件类型分管道解析（替换"Docling统一解析"）

**问题回顾**：Docling 处理 PPTX 时会丢失占位符内图片、忽略图表、内存泄漏。

**修正方案**：每种文件类型使用最稳定的专业解析器：

```python
class DocumentParserRouter:
    """文件类型路由器 - 每种格式用最稳定的工具"""

    def __init__(self):
        self.parsers = {
            ".pdf":   PDFParser(),       # Docling（子进程隔离）
            ".pptx":  PPTXParser(),      # python-pptx（直接提取，最稳定）
            ".docx":  DOCXParser(),      # python-docx 为主 + Docling 辅助
            ".xlsx":  XLSXParser(),      # pandas + openpyxl
            ".md":    MarkdownParser(),  # markdown-it-py
        }

    async def parse(self, file_path: Path) -> UnifiedDocument:
        ext = file_path.suffix.lower()
        parser = self.parsers.get(ext)
        if not parser:
            raise ValueError(f"不支持的格式: {ext}")

        # 所有解析器输出统一的 UnifiedDocument 格式
        return await parser.parse(file_path)


class PPTXParser:
    """PPTX 解析器 - 直接用 python-pptx，不经过 Docling"""

    async def parse(self, file_path: Path) -> UnifiedDocument:
        from pptx import Presentation

        prs = Presentation(str(file_path))
        doc = UnifiedDocument(source=str(file_path))

        for slide_idx, slide in enumerate(prs.slides):
            for shape in slide.shapes:
                # 文字
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        if para.text.strip():
                            doc.add_text(
                                id=f"s{slide_idx}_sh{shape.shape_id}_p{para.level}",
                                content=para.text.strip(),
                                page=slide_idx,
                                bbox=[shape.left, shape.top,
                                      shape.left + shape.width,
                                      shape.top + shape.height],
                                level=para.level,
                            )

                # 图片（包括占位符内的图片）
                if shape.shape_type == 13:  # Picture
                    self._extract_picture(shape, slide_idx, doc)
                elif hasattr(shape, "image"):
                    # 处理占位符内的图片
                    self._extract_placeholder_image(shape, slide_idx, doc)

                # 表格
                if shape.has_table:
                    table_data = [[cell.text for cell in row.cells]
                                  for row in shape.table.rows]
                    doc.add_table(
                        id=f"s{slide_idx}_tbl{shape.shape_id}",
                        data=table_data,
                        page=slide_idx,
                        bbox=[shape.left, shape.top,
                              shape.left + shape.width,
                              shape.top + shape.height],
                    )

                # 图表 → 转为图片 + 数据（python-pptx 可提取图表数据）
                if shape.has_chart:
                    chart_data = self._extract_chart_data(shape)
                    doc.add_table(
                        id=f"s{slide_idx}_chart{shape.shape_id}",
                        data=chart_data,
                        page=slide_idx,
                        bbox=[shape.left, shape.top,
                              shape.left + shape.width,
                              shape.top + shape.height],
                        is_chart=True,
                    )

        return doc

    def _extract_picture(self, shape, slide_idx, doc):
        """提取标准图片"""
        img_bytes = shape.image.blob
        ext = shape.image.content_type.split("/")[-1]
        img_hash = hashlib.md5(img_bytes).hexdigest()[:12]
        img_path = doc.assets_dir / f"s{slide_idx}_{img_hash}.{ext}"

        with open(img_path, "wb") as f:
            f.write(img_bytes)

        doc.add_image(
            id=f"s{slide_idx}_img_{img_hash}",
            path=str(img_path),
            page=slide_idx,
            bbox=[shape.left, shape.top,
                  shape.left + shape.width,
                  shape.top + shape.height],
            hash=img_hash,
        )

    def _extract_placeholder_image(self, shape, slide_idx, doc):
        """提取占位符内的嵌入图片 — Docling 会漏掉的部分"""
        try:
            img_bytes = shape.image.blob
            # ... 同 _extract_picture
        except Exception:
            pass  # 非图片占位符，安全跳过

    def _extract_chart_data(self, shape):
        """提取图表数据为表格"""
        chart = shape.chart
        plot = chart.plots[0]
        data = [["类别"] + [str(s) for s in plot.series]]
        for idx, cat in enumerate(plot.categories):
            row = [str(cat)] + [str(s.values[idx]) for s in plot.series]
            data.append(row)
        return data


class PDFParser:
    """PDF 解析器 - Docling（子进程隔离防止内存泄漏）"""

    async def parse(self, file_path: Path) -> UnifiedDocument:
        import subprocess
        import json

        # 在独立子进程中运行 Docling，处理完自动释放内存
        result = subprocess.run(
            ["python", "-m", "docling_parser", str(file_path)],
            capture_output=True, text=True, timeout=300,
            # 限制子进程内存为 4GB
            # Linux: preexec_fn=lambda: resource.setrlimit(resource.RLIMIT_AS, (4<<30, 4<<30))
        )

        if result.returncode != 0:
            # 降级到 PyMuPDF
            return await self._fallback_pymupdf(file_path)

        parsed = json.loads(result.stdout)
        return self._convert_to_unified(parsed)


class UnifiedDocument:
    """统一输出格式 - 所有解析器都输出这个结构"""
    def __init__(self, source: str):
        self.source = source
        self.texts: list[dict] = []
        self.images: list[dict] = []
        self.tables: list[dict] = []
        self.linkage: list[dict] = []
        self.assets_dir: Path = Path("")

    def add_text(self, **kwargs):
        self.texts.append(kwargs)

    def add_image(self, **kwargs):
        self.images.append(kwargs)

    def add_table(self, **kwargs):
        self.tables.append(kwargs)

    def build_linkage(self):
        """三重策略构建图文关联"""
        # ...空间+结构+语义（同V2）
        pass

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "texts": self.texts,
            "images": self.images,
            "tables": self.tables,
            "linkage": self.linkage,
            "fingerprint": self._compute_fingerprint(),
        }

    def _compute_fingerprint(self) -> dict:
        """计算内容指纹 — 用于保真校验"""
        import hashlib
        text_fingerprints = {
            t["id"]: hashlib.md5(t["content"].encode()).hexdigest()
            for t in self.texts
        }
        image_hashes = {img["id"]: img["hash"] for img in self.images}
        return {
            "text_fingerprints": text_fingerprints,
            "image_hashes": image_hashes,
            "text_count": len(self.texts),
            "image_count": len(self.images),
            "table_count": len(self.tables),
            "total_chars": sum(len(t["content"]) for t in self.texts),
        }
```

### 修正2：混合 PDF 生成引擎（Playwright + WeasyPrint）

**问题回顾**：Chromium 不支持 `page-break-inside: avoid` 对 TR/TD 元素，表格会被切断。

**修正方案**：按页面类型选择最佳引擎：

```python
class HybridPDFGenerator:
    """混合PDF生成引擎 - 每页选最优引擎"""

    def __init__(self):
        self.playwright = PlaywrightRenderer()  # 视觉复杂页
        self.weasyprint = WeasyPrintRenderer()   # 文字表格页
        self.merger = PDFMerger()

    async def generate(self, layout_plan: dict, document: UnifiedDocument) -> Path:
        """逐页选择最佳引擎渲染，最后合并"""
        page_pdfs = []

        for page in layout_plan["pages"]:
            page_type = page["layout_type"]

            if page_type in ("cover", "infographic", "data_card", "hero"):
                # 视觉复杂页 → Playwright（完整CSS Grid/Flexbox支持）
                pdf_bytes = await self.playwright.render(page, document)
                page_pdfs.append(pdf_bytes)

            elif page_type in ("text", "table", "two_column", "text_with_sidebar"):
                # 文字表格页 → WeasyPrint（更好的分页控制，表格不被切断）
                pdf_bytes = await self.weasyprint.render(page, document)
                page_pdfs.append(pdf_bytes)

        # 合并所有页面
        final_pdf = self.merger.merge(page_pdfs)
        return final_pdf


class WeasyPrintRenderer:
    """WeasyPrint 渲染器 - 解决表格分页问题"""

    async def render(self, page: dict, document: UnifiedDocument) -> bytes:
        html = self._build_html(page, document)

        # WeasyPrint 的关键优势：
        # 1. CSS @page 完整支持（分页、页眉页脚、命名页面）
        # 2. 表格分页不会切断行（支持 page-break-inside: avoid on TR）
        # 3. 纯 Python，无需浏览器进程
        # 4. 更小的 PDF 文件体积

        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        return pdf_bytes

    def _build_html(self, page: dict, doc: UnifiedDocument) -> str:
        """构建 WeasyPrint 专用 HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            @page {{
                size: A4;
                margin: 15mm 12mm;
                @bottom-center {{
                    content: counter(page);
                    font-size: 9pt;
                    color: #999;
                }}
            }}
            body {{
                font-family: "Noto Sans SC", "Microsoft YaHei", sans-serif;
                font-size: 11pt;
                line-height: 1.8;
                color: #333;
            }}
            /* 表格分页安全 - WeasyPrint 支持这个 */
            table {{
                width: 100%;
                border-collapse: collapse;
                page-break-inside: avoid;  /* ★ WeasyPrint 支持，Playwright 不支持 */
            }}
            tr {{
                page-break-inside: avoid;  /* ★ 行不被切断 */
            }}
            img {{
                max-width: 100%;
                page-break-inside: avoid;
            }}
            /* 双栏布局 */
            .two-column {{
                columns: 2;
                column-gap: 8mm;
                column-rule: 1px solid #eee;
            }}
        </style>
        </head>
        <body>
            {self._fill_content(page, doc)}
        </body>
        </html>
        """


class PlaywrightRenderer:
    """Playwright 渲染器 - 用于视觉复杂页（封面、数据卡片）"""

    def __init__(self):
        self._browser = None

    async def _get_browser(self):
        if self._browser is None or self._browser._connection is None:
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(
                headless=True,
                args=['--js-flags=--max-old-space-size=2048']
            )
        return self._browser

    async def render(self, page: dict, document: UnifiedDocument) -> bytes:
        browser = await self._get_browser()
        context = await browser.new_context()
        page_obj = await context.new_page()

        try:
            html = self._build_html(page, document)
            await page_obj.set_content(html, wait_until="networkidle")

            # 等待字体加载
            await page_obj.wait_for_timeout(500)

            pdf_bytes = await page_obj.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
            )
            return pdf_bytes
        finally:
            await page_obj.close()
            await context.close()
            # 每 50 次渲染后重启浏览器（防内存泄漏）
            self._render_count = getattr(self, '_render_count', 0) + 1
            if self._render_count >= 50:
                await self._browser.close()
                self._browser = None
                self._render_count = 0
```

### 修正3：PPTX 模板填充模式（不从头生成）

**问题回顾**：python-pptx 中文字体只能用宋体，无法嵌入字体，视觉效果有限。

**修正方案**：**绝不从头生成 PPTX**，而是设计师制作精美模板，代码只做填充：

```python
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
import pptx_ea_font  # 解决中文字体问题

class PPTXTemplateFiller:
    """PPTX 模板填充器 — 保证杂志级质量"""

    # 模板由专业设计师在 PowerPoint 中制作
    # 包含：精美的渐变背景、专业字体（已嵌入）、阴影效果、动画
    # 在需要动态内容的位置放置"魔术占位符"

    def __init__(self, template_path: str):
        self.prs = Presentation(template_path)
        self._fix_fonts()  # 修复中文字体问题

    def _fix_fonts(self):
        """使用 pptx-ea-font 修复中文字体显示"""
        for slide in self.prs.slides:
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        for run in para.runs:
                            # 修复东亚字体渲染
                            pptx_ea_font.setFont(run, "微软雅黑")

    def fill(self, layout_plan: dict, document: UnifiedDocument) -> Path:
        """填充模板 — 只替换文字和图片，不改变设计"""

        for page in layout_plan["pages"]:
            slide_idx = page["page_number"] - 1
            if slide_idx >= len(self.prs.slides):
                # 如果模板页不够，复制最后一页
                self._duplicate_last_slide()

            slide = self.prs.slides[slide_idx]

            for section in page["sections"]:
                # 替换文字占位符
                if section.get("text_id"):
                    text_data = document.find_text(section["text_id"])
                    self._replace_text(slide, section["placeholder"], text_data["content"])

                # 替换图片占位符
                for img_id in section.get("image_ids", []):
                    img_data = document.find_image(img_id)
                    self._replace_image(slide, section["placeholder"], img_data["path"])

                # 替换表格数据
                for tbl_id in section.get("table_ids", []):
                    tbl_data = document.find_table(tbl_id)
                    self._replace_table(slide, section["placeholder"], tbl_data["data"])

        output_path = Path("output.pptx")
        self.prs.save(str(output_path))
        return output_path

    def _replace_text(self, slide, placeholder_name: str, new_text: str):
        """替换指定占位符中的文字"""
        for shape in slide.shapes:
            if shape.has_text_frame:
                for para in shape.text_frame.paragraphs:
                    full_text = para.text
                    if placeholder_name in full_text:
                        for run in para.runs:
                            if placeholder_name in run.text:
                                run.text = run.text.replace(placeholder_name, new_text)
                                # 保持原有格式（字体、颜色、大小）
                                break

    def _replace_image(self, slide, placeholder_name: str, image_path: str):
        """替换指定占位符中的图片"""
        for shape in slide.shapes:
            if shape.shape_type == 13:  # Picture
                # 通过形状名称匹配
                if placeholder_name in shape.name:
                    left, top = shape.left, shape.top
                    width, height = shape.width, shape.height
                    # 删除旧图片
                    sp = shape._element
                    sp.getparent().remove(sp)
                    # 插入新图片到相同位置
                    slide.shapes.add_picture(image_path, left, top, width, height)

    def _duplicate_last_slide(self):
        """复制最后一页（模板不够时）"""
        from lxml import etree
        last_slide = self.prs.slides[-1]
        # 复制 XML 结构
        slide_layout = last_slide.slide_layout
        new_slide = self.prs.slides.add_slide(slide_layout)
        # 复制所有元素
        for shape in last_slide.shapes:
            el = copy.deepcopy(shape._element)
            new_slide.shapes._spTree.append(el)


# 模板目录结构
"""
templates/pptx/
├── product-intro/          # 产品介绍
│   ├── template.pptx       # 15页精美模板（设计师制作）
│   └── config.json         # 占位符映射配置
├── company-profile/        # 企业画册
│   ├── template.pptx
│   └── config.json
├── marketing-brochure/     # 营销手册
│   ├── template.pptx
│   └── config.json
└── technical-doc/          # 技术文档
    ├── template.pptx
    └── config.json

config.json 示例:
{
    "name": "产品介绍模板",
    "pages": [
        {
            "page_number": 1,
            "layout_type": "cover",
            "placeholders": {
                "title": "{{TITLE}}",
                "subtitle": "{{SUBTITLE}}",
                "cover_image": "cover_img"
            }
        },
        {
            "page_number": 2,
            "layout_type": "text_with_image",
            "placeholders": {
                "heading": "{{SECTION_1_TITLE}}",
                "body": "{{SECTION_1_BODY}}",
                "image": "section_1_img"
            }
        }
    ]
}
"""
```

### 修正4：四层内容保真校验管线（核心新增）

**问题回顾**：LLM 可能悄悄改写/增删原文，没有任何检测手段。

**修正方案**：生成前后强制校验，不过关不放行：

```python
import hashlib
from dataclasses import dataclass


@dataclass
class FidelityCheckResult:
    """保真度检查结果"""
    passed: bool
    overall_score: float
    text_completeness: float    # 文字完整性 0-1
    image_completeness: float   # 图片完整性 0-1
    linkage_integrity: float    # 图文关联完整度 0-1
    semantic_fidelity: float    # 语义保真度 0-1
    issues: list[dict]          # 具体问题列表


class ContentFidelityPipeline:
    """四层内容保真校验管线"""

    PASS_THRESHOLD = 0.95  # 95%以上才算通过

    def __init__(self, zhipu_client):
        self.zhipu = zhipu_client

    async def verify(self, original: UnifiedDocument, output_content: dict) -> FidelityCheckResult:
        """执行完整的四层校验"""

        # ===== 第1层：内容指纹完整性校验 =====
        l1_result = self._check_content_fingerprint(original, output_content)

        # ===== 第2层：图文对应关系校验 =====
        l2_result = self._check_linkage_integrity(original, output_content)

        # ===== 第3层：语义保真校验 =====
        l3_result = await self._check_semantic_fidelity(original, output_content)

        # ===== 第4层：综合评分 =====
        overall = (
            l1_result["score"] * 0.35 +
            l2_result["score"] * 0.35 +
            l3_result["score"] * 0.30
        )

        all_issues = l1_result["issues"] + l2_result["issues"] + l3_result["issues"]

        return FidelityCheckResult(
            passed=overall >= self.PASS_THRESHOLD,
            overall_score=overall,
            text_completeness=l1_result["text_score"],
            image_completeness=l1_result["image_score"],
            linkage_integrity=l2_result["score"],
            semantic_fidelity=l3_result["score"],
            issues=all_issues,
        )

    # ------ 第1层：内容指纹完整性 ------

    def _check_content_fingerprint(self, original: UnifiedDocument, output: dict) -> dict:
        """校验所有原始内容是否都被包含在输出中（零遗漏）"""

        issues = []
        original_fp = original._compute_fingerprint()

        # 文字完整性：逐条对比 MD5 指纹
        output_texts = {t["id"]: t["content"] for t in output.get("texts", [])}
        matched_texts = 0
        missing_texts = []

        for orig_text in original.texts:
            orig_md5 = hashlib.md5(orig_text["content"].encode()).hexdigest()
            # 在输出中查找匹配（允许微小格式差异）
            found = False
            for out_text in output.get("texts", []):
                if orig_text["content"].strip() in out_text["content"].strip():
                    found = True
                    matched_texts += 1
                    break
                # 模糊匹配：允许空白差异
                clean_orig = orig_text["content"].strip().replace(" ", "").replace("\n", "")
                clean_out = out_text["content"].strip().replace(" ", "").replace("\n", "")
                if clean_orig == clean_out:
                    found = True
                    matched_texts += 1
                    break

            if not found:
                missing_texts.append({
                    "id": orig_text["id"],
                    "content_preview": orig_text["content"][:50],
                    "page": orig_text.get("page"),
                })

        text_score = matched_texts / max(len(original.texts), 1)

        # 图片完整性：逐张对比 hash
        output_img_hashes = {img["hash"] for img in output.get("images", []) if "hash" in img}
        orig_img_hashes = {img["hash"] for img in original.images if "hash" in img}

        missing_images = orig_img_hashes - output_img_hashes
        image_score = len(orig_img_hashes & output_img_hashes) / max(len(orig_img_hashes), 1)

        if missing_texts:
            issues.append({
                "level": "CRITICAL",
                "type": "missing_text",
                "count": len(missing_texts),
                "details": missing_texts[:10],
            })
        if missing_images:
            issues.append({
                "level": "CRITICAL",
                "type": "missing_image",
                "count": len(missing_images),
            })

        return {
            "score": (text_score + image_score) / 2,
            "text_score": text_score,
            "image_score": image_score,
            "issues": issues,
        }

    # ------ 第2层：图文对应关系校验 ------

    def _check_linkage_integrity(self, original: UnifiedDocument, output: dict) -> dict:
        """校验图片-文字对应关系是否保持不变（零错位）"""

        issues = []
        total_linkages = len(original.linkage)
        preserved = 0

        for link in original.linkage:
            text_id = link["text_id"]
            image_id = link["image_id"]

            # 检查输出中这对关联是否仍然存在
            output_linkages = output.get("linkage", [])
            found = any(
                ol["text_id"] == text_id and ol["image_id"] == image_id
                for ol in output_linkages
            )

            if found:
                preserved += 1
            else:
                issues.append({
                    "level": "HIGH",
                    "type": "broken_linkage",
                    "text_id": text_id,
                    "image_id": image_id,
                    "message": f"图文关联已断开: {text_id} ↔ {image_id}",
                })

        score = preserved / max(total_linkages, 1)
        return {"score": score, "issues": issues}

    # ------ 第3层：语义保真校验 ------

    async def _check_semantic_fidelity(self, original: UnifiedDocument, output: dict) -> dict:
        """校验文字意思是否被篡改（通过智谱API对比）"""

        issues = []
        total_checked = 0
        faithful_count = 0

        for orig_text in original.texts:
            orig_content = orig_text["content"].strip()
            if len(orig_content) < 10:  # 太短的内容跳过
                continue

            # 在输出中找到对应文字
            output_text = self._find_matching_output_text(orig_text["id"], output)
            if not output_text:
                continue

            total_checked += 1

            # 使用智谱 API 做语义对比（而不是本地模型）
            fidelity = await self._check_single_text_fidelity(orig_content, output_text)
            if fidelity["is_faithful"]:
                faithful_count += 1
            else:
                issues.append({
                    "level": "MEDIUM",
                    "type": "semantic_drift",
                    "text_id": orig_text["id"],
                    "similarity": fidelity["similarity"],
                    "message": fidelity.get("explanation", ""),
                })

        score = faithful_count / max(total_checked, 1)
        return {"score": score, "issues": issues}

    async def _check_single_text_fidelity(self, original: str, processed: str) -> dict:
        """使用智谱 API 检查单段文字的语义保真度"""
        import instructor
        from pydantic import BaseModel, Field

        class FidelityResult(BaseModel):
            is_faithful: bool = Field(description="处理后的文字是否忠于原文")
            similarity: float = Field(description="语义相似度 0-1")
            explanation: str = Field(description="如有偏差，说明具体哪里不同")

        # 使用 Instructor + 智谱 API
        result = await self.zhipu.analyze(
            system_prompt="""你是一个文字校验专家。判断"处理后文字"是否完全忠于"原始文字"。
规则：不允许添加信息、不允许删除信息、不允许修改意思。允许的仅是：格式调整、分段、标点优化。
输出JSON。""",
            user_content=f"原始文字:\n{original}\n\n处理后文字:\n{processed}",
            response_model=FidelityResult,
        )
        return result.dict()

    def _find_matching_output_text(self, text_id: str, output: dict) -> str | None:
        for t in output.get("texts", []):
            if t.get("id") == text_id:
                return t["content"]
        return None
```

### 修正5：子进程隔离 + 内存管理

```python
import subprocess
import resource
import os


class IsolatedDoclingRunner:
    """在隔离子进程中运行 Docling（防止内存泄漏影响主进程）"""

    async def parse_pdf(self, file_path: Path) -> dict:
        """在独立子进程中运行，处理完自动释放内存"""
        script = f"""
import json
import sys
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("{file_path}")

output = {{
    "texts": [],
    "images": [],
    "tables": [],
}}

for item, text_level in result.document.iterate_items():
    element = {{
        "id": item.id,
        "type": str(item.label),
        "content": item.text if hasattr(item, 'text') else "",
    }}
    if hasattr(item, 'prov') and item.prov:
        element["bbox"] = [item.prov[0].bbox.l, item.prov[0].bbox.t,
                          item.prov[0].bbox.r, item.prov[0].bbox.b]
        element["page"] = item.prov[0].page_no
    output["texts"].append(element)

json.dump(output, sys.stdout, ensure_ascii=False)
"""
        try:
            result = subprocess.run(
                ["python", "-c", script],
                capture_output=True, text=True, timeout=300,
                memory_limit=4 * 1024 * 1024 * 1024,  # 4GB 内存限制
            )
            if result.returncode != 0:
                return await self._fallback_pymupdf(file_path)
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return await self._fallback_pymupdf(file_path)
        except Exception:
            return await self._fallback_pymupdf(file_path)

    async def _fallback_pymupdf(self, file_path: Path) -> dict:
        """降级到 PyMuPDF（100%稳定，不会内存泄漏）"""
        import fitz
        doc = fitz.open(str(file_path))
        # ... PyMuPDF 解析逻辑（同V1）
        doc.close()
        return output
```

---

## 三、完整的 LangGraph 工作流（含保真校验节点）

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict


class PipelineState(TypedDict):
    # 输入
    file_path: str
    session_id: str
    output_format: str  # "pdf" | "pptx"
    template_id: str

    # 解析
    parsed_document: UnifiedDocument
    parse_error: str | None

    # 分析
    document_structure: dict
    layout_plan: dict

    # 素材
    supplemented_assets: list[dict]

    # 生成
    output_path: str

    # ★ 保真校验
    fidelity_result: FidelityCheckResult
    needs_manual_review: bool


def build_production_pipeline():
    graph = StateGraph(PipelineState)

    # 节点
    graph.add_node("parse", parse_document)           # 按文件类型路由
    graph.add_node("link", build_linkage)              # 三重策略关联
    graph.add_node("analyze", analyze_with_zhipu)      # 语义分析
    graph.add_node("plan_layout", plan_magazine_layout)# 排版规划
    graph.add_node("supplement", supplement_assets)    # 素材补充
    graph.add_node("generate", generate_output)        # 混合引擎生成
    graph.add_node("verify", verify_fidelity)          # ★ 四层保真校验
    graph.add_node("repair", attempt_auto_repair)      # ★ 自动修复
    graph.add_node("finalize", finalize_output)        # 输出

    # 流程
    graph.set_entry_point("parse")
    graph.add_edge("parse", "link")
    graph.add_edge("link", "analyze")
    graph.add_edge("analyze", "plan_layout")

    # 条件分支：素材不足时补充
    graph.add_conditional_edges(
        "plan_layout",
        lambda s: "supplement" if s.get("missing_assets") else "generate",
        {"supplement": "supplement", "generate": "generate"},
    )
    graph.add_edge("supplement", "generate")

    # 生成 → 保真校验
    graph.add_edge("generate", "verify")

    # 条件分支：校验不过关 → 自动修复 → 重新校验（最多2次）
    graph.add_conditional_edges(
        "verify",
        lambda s: "repair" if not s["fidelity_result"].passed and s.get("repair_count", 0) < 2 else "finalize",
        {"repair": "repair", "finalize": "finalize"},
    )
    graph.add_edge("repair", "verify")

    graph.add_edge("finalize", END)

    return graph.compile()


async def verify_fidelity(state: PipelineState) -> PipelineState:
    """四层保真校验节点"""
    pipeline = ContentFidelityPipeline(zhipu_client=ZhipuClient(state["session_id"]))

    result = await pipeline.verify(
        original=state["parsed_document"],
        output_content=state["layout_plan"],  # 排版方案中的内容
    )

    state["fidelity_result"] = result
    state["needs_manual_review"] = not result.passed

    if not result.passed:
        # 生成详细报告供前端展示
        report = format_fidelity_report(result)
        state["fidelity_report"] = report

    return state


async def attempt_auto_repair(state: PipelineState) -> PipelineState:
    """自动修复：根据校验问题尝试修复"""
    repair_count = state.get("repair_count", 0)
    state["repair_count"] = repair_count + 1

    for issue in state["fidelity_result"].issues:
        if issue["level"] == "CRITICAL" and issue["type"] == "missing_text":
            # 将缺失的文字重新添加到排版方案中
            for missing in issue["details"]:
                text = state["parsed_document"].find_text(missing["id"])
                if text:
                    append_to_layout(state["layout_plan"], text, missing["page"])

        elif issue["level"] == "CRITICAL" and issue["type"] == "missing_image":
            # 将缺失的图片重新添加
            pass

        elif issue["level"] == "HIGH" and issue["type"] == "broken_linkage":
            # 恢复断开的图文关联
            restore_linkage(state["layout_plan"], issue)

    return state
```

---

## 四、前端保真报告界面

```typescript
// 校验报告展示组件
interface FidelityReportProps {
  result: FidelityCheckResult
}

function FidelityReport({ result }: FidelityReportProps) {
  return (
    <div className="fidelity-report">
      {/* 总体评分 */}
      <ScoreGauge score={result.overall_score} threshold={0.95} />

      {/* 四层校验结果 */}
      <div className="check-layers">
        <CheckItem
          label="文字完整性"
          score={result.text_completeness}
          status={result.text_completeness >= 0.99 ? 'pass' : 'fail'}
          description={`共 ${result.text_count} 段文字，遗漏 ${result.missing_texts} 段`}
        />
        <CheckItem
          label="图片完整性"
          score={result.image_completeness}
          status={result.image_completeness >= 0.99 ? 'pass' : 'fail'}
          description={`共 ${result.image_count} 张图片，遗漏 ${result.missing_images} 张`}
        />
        <CheckItem
          label="图文关联完整度"
          score={result.linkage_integrity}
          status={result.linkage_integrity >= 0.95 ? 'pass' : 'fail'}
        />
        <CheckItem
          label="语义保真度"
          score={result.semantic_fidelity}
          status={result.semantic_fidelity >= 0.95 ? 'pass' : 'fail'}
        />
      </div>

      {/* 问题列表 */}
      {result.issues.length > 0 && (
        <div className="issues">
          <h3>需要确认的问题</h3>
          {result.issues.map((issue, i) => (
            <IssueCard key={i} issue={issue} onConfirm={handleConfirm} />
          ))}
        </div>
      )}
    </div>
  )
}
```

---

## 五、最终开源组件清单

| 模块 | 组件 | 协议 | 用途 | 稳定性评级 |
|------|------|------|------|-----------|
| **PDF解析** | Docling (子进程) | MIT | PDF 结构化解析 | ⭐⭐⭐⭐ |
| **PPTX解析** | python-pptx | MIT | PPTX 图片+文字+坐标 | ⭐⭐⭐⭐⭐ |
| **DOCX解析** | python-docx | MIT | Word 文档解析 | ⭐⭐⭐⭐⭐ |
| **XLSX解析** | openpyxl | MIT | Excel 解析 | ⭐⭐⭐⭐⭐ |
| **PDF降级** | PyMuPDF | AGPL | Docling 失败时降级 | ⭐⭐⭐⭐⭐ |
| **PDF视觉页** | Playwright | Apache-2.0 | 封面/数据卡片渲染 | ⭐⭐⭐⭐ |
| **PDF文字页** | WeasyPrint | BSD-3 | 正文/表格页渲染 | ⭐⭐⭐⭐⭐ |
| **PPTX生成** | python-pptx + pptx-ea-font | MIT | 模板填充模式 | ⭐⭐⭐⭐ |
| **PDF合并** | PyPDF | BSD-3 | 混合PDF页面合并 | ⭐⭐⭐⭐⭐ |
| **工作流** | LangGraph | MIT | 状态图编排 | ⭐⭐⭐⭐⭐ |
| **LLM调用** | Instructor | MIT | 结构化输出 | ⭐⭐⭐⭐⭐ |
| **语义分析** | 智谱GLM-5 API | 商业 | 语义分析+保真校验 | ⭐⭐⭐⭐ |
| **素材搜索** | Unsplash/Pexels API | 免费 | 免费商用素材 | ⭐⭐⭐⭐⭐ |
| **AI生图** | Replicate FLUX.1 | 商业 | 缺失素材生成 | ⭐⭐⭐⭐ |
| **去背景** | rembg | MIT | 素材背景移除 | ⭐⭐⭐⭐⭐ |
| **后端** | FastAPI | MIT | API 服务 | ⭐⭐⭐⭐⭐ |
| **前端** | Next.js | MIT | 用户界面 | ⭐⭐⭐⭐⭐ |

---

## 六、最终 Docker Compose（7个容器）

```yaml
services:
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  backend:
    build: ./backend        # 含 Playwright + WeasyPrint + Docling
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    volumes:
      - ./data/uploads:/app/uploads
      - ./data/output:/app/output
      - ./data/templates:/app/templates   # 杂志模板
    depends_on: [redis, minio]

  redis:
    image: redis:7-alpine

  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes: [./nginx/nginx.conf:/etc/nginx/nginx.conf:ro]
```

> 实际只有 5 个容器（frontend + backend + redis + minio + nginx）
> Docling、Playwright、WeasyPrint 全部打包在 backend 容器中

---

## 七、最终硬件要求

| 配置 | 最低 | 推荐 |
|------|------|------|
| CPU | 4核 | 8核 |
| 内存 | **8GB** | 16GB |
| 存储 | 50GB SSD | 200GB SSD |
| GPU | 不需要 | 不需要 |

> 8GB 是因为 Docling 子进程需要独立内存（4GB限制），加上 Playwright 浏览器（~2GB）。

---

## 八、最终成本估算

| 服务 | 月成本（100份文档） |
|------|---------------------|
| 智谱 GLM-5 Pro（分析+校验×2） | ~60元 |
| Replicate（仅缺图时生图） | ~10元 |
| 云服务器 8核8GB | ~150元 |
| **总计** | **~220元/月** |

> 保真校验多调用一次智谱 API，成本增加约30元/月，但换来质量保证。

---

## 九、最终开发计划（7周）

| 周 | 任务 | 交付物 |
|----|------|--------|
| 1 | 项目骨架 + 文件类型路由器 + 各格式解析器 | 解析器可独立测试 |
| 2 | 图文关联算法 + 内容指纹系统 | 关联准确率可量化 |
| 3 | 智谱集成 + Instructor + 语义分析 | 结构化分析输出 |
| 4 | 混合PDF引擎 + PPTX模板填充 + 杂志模板 | 可生成PDF/PPTX |
| 5 | 四层保真校验管线 + 自动修复 + 降级策略 | 校验报告可视化 |
| 6 | 素材补充系统 + 前端界面 | 完整用户流程 |
| 7 | 50份边界测试 + 性能优化 + Docker发布 | 生产就绪 |

---

## 十、V3 vs V2 vs V1 最终对比

| 维度 | V1 | V2 | V3（最终） |
|------|----|----|-----------|
| 文档解析 | 5个库拼接 | Docling 统一 | **按格式分管道+降级** |
| PDF生成 | Typst | Playwright | **Playwright+WeasyPrint混合** |
| PPTX生成 | python-pptx从零建 | 同V1 | **模板填充模式** |
| 工作流 | Dify(10容器) | LangGraph | **LangGraph+保真校验** |
| 内容保真 | 无 | 简单检查 | **四层校验管线** |
| 容器数 | 10 | 6 | **5** |
| 内存要求 | 8GB | 4GB | **8GB（含降级安全）** |
| 稳定性 | 低 | 中 | **高（每层有降级方案）** |
| 输出质量 | 中 | 高 | **高+可验证** |
