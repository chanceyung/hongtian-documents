# 杂志级文档重构智能体 V4 — 完整实现代码

> 本文档是 INTEGRATION_GUIDE_V4.md 的补充，提供所有未实现的模块完整代码。
> 所有代码基于 Presenton 项目结构，可直接集成。

---

## 一、完整的 Supplement Agent（素材补充智能体）

```python
# backend/app/agents/supplement_agent.py
"""素材补充智能体：搜索 + AI生图 + 背景移除"""

import httpx
import hashlib
import base64
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

from app.models.unified_document import UnifiedDocument, ImageElement
from app.models.edit_actions import MagazineEditPlan, EditAction


class SupplementRequest(BaseModel):
    text_context: str          # 需要配图的文字内容
    style: str = "professional"  # professional | creative | minimal
    width: int = 1920
    height: int = 1080


class SupplementAgent:
    """补充缺失素材：优先搜索免费图库，必要时 AI 生图"""

    def __init__(self, session_id: str):
        self.session_id = session_id
        from app.core.config import settings
        self.unsplash_key = settings.UNSPLASH_ACCESS_KEY
        self.pexels_key = settings.PEXELS_API_KEY
        self.output_dir = Path(settings.ASSETS_DIR) / session_id / "supplemented"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def supplement(
        self,
        doc: UnifiedDocument,
        plan: MagazineEditPlan,
    ) -> None:
        """扫描编辑计划，为所有缺失图片补充素材"""

        for page in plan.pages:
            for action in page.actions:
                if action.type != "replace_image":
                    continue

                # 检查图片是否存在
                img = next(
                    (i for i in doc.images if i.id == action.source_id), None
                )
                if img and Path(img.local_path).exists() and Path(img.local_path).stat().st_size > 0:
                    continue  # 图片已存在，跳过

                # 找到关联的文字作为搜索上下文
                context = self._find_text_context(doc, action.source_id, page)

                # 尝试补充
                supplemented_path = await self._try_supplement(context, action.source_id)
                if supplemented_path:
                    # 更新文档中的图片信息
                    if img:
                        img.local_path = str(supplemented_path)
                    else:
                        # 创建新的 ImageElement
                        new_img = ImageElement(
                            id=action.source_id,
                            local_path=str(supplemented_path),
                            page=0,
                            hash=hashlib.md5(supplemented_path.read_bytes()).hexdigest()[:12],
                        )
                        doc.images.append(new_img)

    def _find_text_context(
        self, doc: UnifiedDocument, image_id: str, page
    ) -> str:
        """找到与图片关联的文字内容作为搜索上下文"""
        # 从关联关系中查找
        for link in doc.linkage:
            if link.asset_id == image_id and link.asset_type == "image":
                text = next(
                    (t for t in doc.texts if t.id == link.text_id), None
                )
                if text:
                    return text.content[:300]

        # 降级：使用同页文字
        page_texts = [
            t.content for t in doc.texts
            if t.page == page.page_number - 1
        ]
        return " ".join(page_texts)[:300]

    async def _try_supplement(
        self, context: str, image_id: str
    ) -> Optional[Path]:
        """三级降级：Pexels → Unsplash → AI 生图"""
        # 第一选择：Pexels（免费，无需归属）
        path = await self._search_pexels(context, image_id)
        if path:
            return path

        # 第二选择：Unsplash
        path = await self._search_unsplash(context, image_id)
        if path:
            return path

        # 最后选择：AI 生图（通过 Replicate API）
        path = await self._generate_image(context, image_id)
        return path

    async def _search_pexels(
        self, context: str, image_id: str
    ) -> Optional[Path]:
        """从 Pexels 搜索免费图片"""
        if not self.pexels_key:
            return None

        keywords = await self._extract_keywords(context)
        if not keywords:
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": self.pexels_key},
                    params={
                        "query": keywords,
                        "per_page": 3,
                        "orientation": "landscape",
                        "size": "large",
                    },
                )
                if resp.status_code != 200:
                    return None

                photos = resp.json().get("photos", [])
                if not photos:
                    return None

                # 下载第一张高质量图片
                photo = photos[0]
                img_url = photo["src"]["large2x"]

                img_resp = await client.get(img_url)
                if img_resp.status_code != 200:
                    return None

                img_hash = hashlib.md5(img_resp.content).hexdigest()[:12]
                img_path = self.output_dir / f"{image_id}_{img_hash}.jpg"
                img_path.write_bytes(img_resp.content)

                return img_path
            except Exception:
                return None

    async def _search_unsplash(
        self, context: str, image_id: str
    ) -> Optional[Path]:
        """从 Unsplash 搜索图片"""
        if not self.unsplash_key:
            return None

        keywords = await self._extract_keywords(context)
        if not keywords:
            return None

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                resp = await client.get(
                    "https://api.unsplash.com/search/photos",
                    headers={"Authorization": f"Client-ID {self.unsplash_key}"},
                    params={
                        "query": keywords,
                        "per_page": 3,
                        "orientation": "landscape",
                    },
                )
                if resp.status_code != 200:
                    return None

                results = resp.json().get("results", [])
                if not results:
                    return None

                photo = results[0]
                img_url = photo["urls"]["regular"]

                img_resp = await client.get(
                    img_url,
                    headers={"Accept-Version": "v1"},
                )
                if img_resp.status_code != 200:
                    return None

                img_hash = hashlib.md5(img_resp.content).hexdigest()[:12]
                img_path = self.output_dir / f"{image_id}_{img_hash}.jpg"
                img_path.write_bytes(img_resp.content)

                return img_path
            except Exception:
                return None

    async def _generate_image(
        self, context: str, image_id: str
    ) -> Optional[Path]:
        """通过 Replicate API 使用 Flux.1 生成图片"""
        from app.core.config import settings
        replicate_token = getattr(settings, "REPLICATE_API_TOKEN", "")
        if not replicate_token:
            return None

        # 先通过 GLM-5 生成英文 prompt
        prompt = await self._generate_image_prompt(context)

        async with httpx.AsyncClient(timeout=120) as client:
            try:
                # 创建生成任务
                resp = await client.post(
                    "https://api.replicate.com/v1/models/black-forest-labs/flux-1-schnell/predictions",
                    headers={
                        "Authorization": f"Token {replicate_token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "input": {
                            "prompt": prompt,
                            "width": 1344,
                            "height": 768,
                            "num_outputs": 1,
                        }
                    },
                )
                if resp.status_code not in (200, 201):
                    return None

                prediction = resp.json()
                prediction_id = prediction["id"]

                # 轮询等待结果（最多 60 秒）
                import asyncio
                for _ in range(30):
                    await asyncio.sleep(2)
                    status_resp = await client.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers={"Authorization": f"Token {replicate_token}"},
                    )
                    status_data = status_resp.json()

                    if status_data["status"] == "succeeded":
                        output_url = status_data["output"][0]
                        img_resp = await client.get(output_url)
                        img_hash = hashlib.md5(img_resp.content).hexdigest()[:12]
                        img_path = self.output_dir / f"{image_id}_{img_hash}.png"
                        img_path.write_bytes(img_resp.content)
                        return img_path

                    if status_data["status"] == "failed":
                        return None

                return None  # 超时
            except Exception:
                return None

    async def _extract_keywords(self, context: str) -> str:
        """用 GLM-5 从文字中提取图片搜索关键词"""
        from app.services.zhipu_client import ZhipuClient
        client = ZhipuClient(self.session_id)
        try:
            keywords = await client.generate_search_keywords(context)
            if isinstance(keywords, list):
                return " ".join(keywords[:3])
            return str(keywords)
        except Exception:
            # 降级：取文字前几个词
            words = context.split()[:5]
            return " ".join(words)

    async def _generate_image_prompt(self, context: str) -> str:
        """用 GLM-5 生成英文 AI 绘图 prompt"""
        from app.services.zhipu_client import ZhipuClient
        client = ZhipuClient(self.session_id)
        try:
            return await client.generate_image_prompt(context)
        except Exception:
            return f"professional business presentation illustration, {context[:100]}, high quality, clean background"
```

---

## 二、完整的 Fidelity Agent（四层保真校验智能体）

```python
# backend/app/agents/fidelity_agent.py
"""四层保真校验：指纹 → 关联 → 语义 → 人工"""

import hashlib
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel
from typing import Literal

from app.models.unified_document import UnifiedDocument, ContentFingerprint
from app.models.edit_actions import MagazineEditPlan


class FidelityIssue(BaseModel):
    level: Literal["critical", "warning", "info"]
    category: str          # fingerprint | linkage | semantic | human
    description: str
    element_id: str = ""
    original: str = ""
    generated: str = ""


class FidelityResult(BaseModel):
    overall_score: float
    passed: bool
    l1_score: float = 0.0   # 指纹完整性
    l2_score: float = 0.0   # 关联完整性
    l3_score: float = 0.0   # 语义保真度
    l4_required: bool = False  # 是否需要人工确认
    issues: list[FidelityIssue] = []


class FidelityAgent:
    """四层保真校验"""

    def __init__(
        self,
        api_key: str,
        threshold: float = 0.95,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
    ):
        self.client = instructor.from_openai(
            AsyncOpenAI(api_key=api_key, base_url=base_url)
        )
        self.threshold = threshold

    async def verify(
        self, doc: UnifiedDocument, plan: MagazineEditPlan
    ) -> FidelityResult:
        """执行四层保真校验"""

        issues: list[FidelityIssue] = []

        # L1: 内容指纹完整性
        l1_score, l1_issues = self._check_fingerprint(doc, plan)
        issues.extend(l1_issues)

        # L2: 图文关联完整性
        l2_score, l2_issues = self._check_linkage(doc, plan)
        issues.extend(l2_issues)

        # L3: 语义保真度（调用 GLM-5）
        l3_score, l3_issues = await self._check_semantic(doc, plan)
        issues.extend(l3_issues)

        # L4: 判断是否需要人工确认
        l4_required = (
            l1_score < 1.0
            or l2_score < 0.9
            or l3_score < 0.9
            or any(i.level == "critical" for i in issues)
        )

        # 综合得分（加权）
        overall = l1_score * 0.4 + l2_score * 0.3 + l3_score * 0.3

        return FidelityResult(
            overall_score=round(overall, 4),
            passed=overall >= self.threshold and not l4_required,
            l1_score=l1_score,
            l2_score=l2_score,
            l3_score=l3_score,
            l4_required=l4_required,
            issues=issues,
        )

    def _check_fingerprint(
        self, doc: UnifiedDocument, plan: MagazineEditPlan
    ) -> tuple[float, list[FidelityIssue]]:
        """L1: 内容指纹——确保所有原文内容都被包含"""

        original_fp = doc.compute_fingerprint()
        issues = []

        # 收集编辑计划中覆盖的元素
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

        # 检查文字遗漏
        missing_texts = []
        for t in doc.texts:
            if t.id not in planned_text_ids:
                missing_texts.append(t)

        if missing_texts:
            issues.append(FidelityIssue(
                level="critical",
                category="fingerprint",
                description=f"遗漏 {len(missing_texts)} 段文字",
                element_id=missing_texts[0].id,
                original=missing_texts[0].content[:100],
            ))

        # 检查图片遗漏
        missing_images = [i for i in doc.images if i.id not in planned_image_ids]
        if missing_images:
            issues.append(FidelityIssue(
                level="critical",
                category="fingerprint",
                description=f"遗漏 {len(missing_images)} 张图片",
                element_id=missing_images[0].id,
            ))

        # 检查表格遗漏
        missing_tables = [t for t in doc.tables if t.id not in planned_table_ids]
        if missing_tables:
            issues.append(FidelityIssue(
                level="warning",
                category="fingerprint",
                description=f"遗漏 {len(missing_tables)} 个表格",
            ))

        # 计算完整性分数
        total = len(doc.texts) + len(doc.images) + len(doc.tables)
        covered = len(planned_text_ids & {t.id for t in doc.texts}) \
                + len(planned_image_ids & {i.id for i in doc.images}) \
                + len(planned_table_ids & {t.id for t in doc.tables})
        score = covered / total if total > 0 else 1.0

        return score, issues

    def _check_linkage(
        self, doc: UnifiedDocument, plan: MagazineEditPlan
    ) -> tuple[float, list[FidelityIssue]]:
        """L2: 图文关联完整性"""

        issues = []

        # 检查关联关系是否被保留
        broken_links = []
        for link in doc.linkage:
            text_in_plan = False
            asset_in_plan = False

            for page in plan.pages:
                for action in page.actions:
                    if action.source_id == link.text_id:
                        text_in_plan = True
                    if action.source_id == link.asset_id:
                        asset_in_plan = True

            if link.confidence >= 0.7 and not (text_in_plan and asset_in_plan):
                broken_links.append(link)

        if broken_links:
            issues.append(FidelityIssue(
                level="warning",
                category="linkage",
                description=f"{len(broken_links)} 个图文关联被打破",
                element_id=broken_links[0].text_id,
            ))

        total_links = len([l for l in doc.linkage if l.confidence >= 0.7])
        intact = total_links - len(broken_links)
        score = intact / total_links if total_links > 0 else 1.0

        return score, issues

    async def _check_semantic(
        self, doc: UnifiedDocument, plan: MagazineEditPlan
    ) -> tuple[float, list[FidelityIssue]]:
        """L3: 语义保真度——对比原文和生成内容是否语义一致"""

        issues = []

        # 抽样检查（最多10个文字）
        sampled_actions = []
        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_text" and action.content:
                    sampled_actions.append(action)
        sampled_actions = sampled_actions[:10]

        if not sampled_actions:
            return 1.0, []

        # 构建对比文本
        comparisons = []
        for action in sampled_actions:
            original = next(
                (t for t in doc.texts if t.id == action.source_id), None
            )
            if original:
                comparisons.append({
                    "id": original.id,
                    "original": original.content,
                    "generated": action.content,
                })

        if not comparisons:
            return 1.0, []

        # 调用 GLM-5 进行语义对比
        class SemanticCheckResult(BaseModel):
            comparisons: list[dict]
            overall_fidelity: float

        result = await self.client.chat.completions.create(
            model="glm-5-pro",
            response_model=SemanticCheckResult,
            messages=[
                {
                    "role": "system",
                    "content": """你是内容保真校验专家。对比原始文字和生成文字，判断语义是否一致。
规则：
1. 只检查含义是否相同，不要求措辞完全一样
2. 数据、数字、专有名词必须100%一致
3. 每个对比给出 faithful(true/false) 和说明
4. overall_fidelity = faithful数量 / 总数量""",
                },
                {
                    "role": "user",
                    "content": str(comparisons),
                },
            ],
            temperature=0.0,
        )

        # 解析结果
        unfaithful = [
            c for c in result.comparisons
            if not c.get("faithful", True)
        ]

        for u in unfaithful:
            orig = next(
                (c for c in comparisons if c["id"] == u.get("id", "")), None
            )
            issues.append(FidelityIssue(
                level="critical",
                category="semantic",
                description=u.get("reason", "语义不一致"),
                element_id=u.get("id", ""),
                original=orig["original"][:100] if orig else "",
                generated=u.get("generated", "")[:100],
            ))

        score = result.overall_fidelity
        return score, issues
```

---

## 三、完整的多格式解析器

### 3.1 PDF 解析器（Docling 子进程隔离 + PyMuPDF 降级）

```python
# backend/app/parsers/pdf_parser.py
"""PDF 解析：Docling（子进程隔离）+ PyMuPDF 降级"""

import asyncio
import json
import hashlib
from pathlib import Path
from typing import Optional

from app.models.unified_document import (
    UnifiedDocument, TextElement, ImageElement,
    TableElement, BoundingBox,
)


class PdfParser:
    """PDF 解析器：双引擎策略"""

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        """先尝试 Docling，失败则降级 PyMuPDF"""
        try:
            return await self._parse_docling(path, session_id)
        except Exception as e:
            doc = UnifiedDocument(
                source_file=str(path),
                source_format="pdf",
                parse_warnings=[f"Docling 失败({str(e)[:100]})，降级到 PyMuPDF"],
            )
            return await self._parse_pymupdf(path, doc)

    async def _parse_docling(
        self, path: Path, session_id: str
    ) -> UnifiedDocument:
        """Docling 子进程隔离解析（解决内存泄漏问题）"""

        output_dir = path.parent / "docling_output"
        output_dir.mkdir(exist_ok=True)

        # 子进程运行 Docling（隔离内存）
        script = f"""
import json
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("{str(path)}")

output = {{
    "texts": [],
    "tables": [],
}}

for item in result.document.iterate_items():
    if hasattr(item, "text"):
        output["texts"].append({{
            "content": item.text,
            "page": getattr(item, "prov", [{{}}])[0].get("page_no", 0) if hasattr(item, "prov") and item.prov else 0,
        }})
    if hasattr(item, "data"):
        output["tables"].append({{
            "data": item.data,
            "page": getattr(item, "prov", [{{}}])[0].get("page_no", 0) if hasattr(item, "prov") and item.prov else 0,
        }})

with open("{str(output_dir / "result.json")}", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False)
"""
        script_path = output_dir / "docling_parse.py"
        script_path.write_text(script, encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            "python", str(script_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=300
        )

        if proc.returncode != 0:
            raise RuntimeError(
                f"Docling 进程失败: {stderr.decode()[:500]}"
            )

        # 读取结果
        result_path = output_dir / "result.json"
        if not result_path.exists():
            raise FileNotFoundError("Docling 输出文件不存在")

        with open(result_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        doc = UnifiedDocument(
            source_file=str(path),
            source_format="pdf",
            parse_method="docling",
        )

        for idx, t in enumerate(data.get("texts", [])):
            doc.texts.append(TextElement(
                id=f"pdf_t{idx}",
                content=t["content"],
                page=t.get("page", 0),
                fingerprint=hashlib.md5(t["content"].encode()).hexdigest(),
            ))

        for idx, tbl in enumerate(data.get("tables", [])):
            doc.tables.append(TableElement(
                id=f"pdf_tbl{idx}",
                page=tbl.get("page", 0),
                data=tbl.get("data", []),
            ))

        # 用 PyMuPDF 补充图片（Docling 不擅长提取图片位置）
        doc = await self._supplement_images_pymupdf(path, doc)

        return doc

    async def _parse_pymupdf(
        self, path: Path, doc: UnifiedDocument
    ) -> UnifiedDocument:
        """PyMuPDF 降级解析"""
        import fitz

        pdf = fitz.open(str(path))
        doc.total_pages = len(pdf)
        doc.parse_method = "pymupdf"

        assets_dir = path.parent / "assets"
        assets_dir.mkdir(exist_ok=True)

        for page_num in range(len(pdf)):
            page = pdf[page_num]

            # 提取文字块
            blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block["type"] != 0:
                    continue

                for line in block.get("lines", []):
                    text = "".join(span["text"] for span in line.get("spans", []))
                    if not text.strip():
                        continue

                    # 推断标题级别
                    max_size = max(
                        (span.get("size", 12) for span in line.get("spans", [])),
                        default=12,
                    )
                    level = 1 if max_size > 20 else (2 if max_size > 16 else 0)

                    bbox = block["bbox"]
                    doc.texts.append(TextElement(
                        id=f"pdf_p{page_num}_t{len(doc.texts)}",
                        content=text.strip(),
                        page=page_num,
                        bbox=BoundingBox(
                            left=int(bbox[0] * 12700),   # pt → EMU
                            top=int(bbox[1] * 12700),
                            width=int((bbox[2] - bbox[0]) * 12700),
                            height=int((bbox[3] - bbox[1]) * 12700),
                        ),
                        level=level,
                        fingerprint=hashlib.md5(text.strip().encode()).hexdigest(),
                    ))

            # 提取图片
            for img_idx, img_info in enumerate(page.get_images(full=True)):
                xref = img_info[0]
                try:
                    base_image = pdf.extract_image(xref)
                    if not base_image:
                        continue

                    img_bytes = base_image["image"]
                    ext = base_image["ext"]
                    img_hash = hashlib.md5(img_bytes).hexdigest()[:12]

                    img_path = assets_dir / f"p{page_num}_img{img_idx}_{img_hash}.{ext}"
                    img_path.write_bytes(img_bytes)

                    # 获取图片位置
                    rects = page.get_image_rects(xref)
                    bbox_pts = list(rects[0]) if rects else [0, 0, 100, 100]

                    doc.images.append(ImageElement(
                        id=f"pdf_p{page_num}_img{img_hash}",
                        local_path=str(img_path),
                        page=page_num,
                        bbox=BoundingBox(
                            left=int(bbox_pts[0] * 12700),
                            top=int(bbox_pts[1] * 12700),
                            width=int((bbox_pts[2] - bbox_pts[0]) * 12700),
                            height=int((bbox_pts[3] - bbox_pts[1]) * 12700),
                        ),
                        width=base_image.get("width", 0),
                        height=base_image.get("height", 0),
                        hash=img_hash,
                    ))
                except Exception:
                    doc.parse_warnings.append(
                        f"Page {page_num}: 图片提取失败 xref={xref}"
                    )

        pdf.close()
        return doc

    async def _supplement_images_pymupdf(
        self, path: Path, doc: UnifiedDocument
    ) -> UnifiedDocument:
        """用 PyMuPDF 为 Docling 结果补充图片"""
        import fitz

        pdf = fitz.open(str(path))
        doc.total_pages = len(pdf)

        assets_dir = path.parent / "assets"
        assets_dir.mkdir(exist_ok=True)

        for page_num in range(len(pdf)):
            page = pdf[page_num]
            for img_idx, img_info in enumerate(page.get_images(full=True)):
                xref = img_info[0]
                try:
                    base_image = pdf.extract_image(xref)
                    if not base_image or base_image.get("width", 0) < 50:
                        continue

                    img_bytes = base_image["image"]
                    ext = base_image["ext"]
                    img_hash = hashlib.md5(img_bytes).hexdigest()[:12]

                    img_path = assets_dir / f"p{page_num}_img{img_idx}_{img_hash}.{ext}"
                    img_path.write_bytes(img_bytes)

                    doc.images.append(ImageElement(
                        id=f"pdf_p{page_num}_img{img_hash}",
                        local_path=str(img_path),
                        page=page_num,
                        width=base_image.get("width", 0),
                        height=base_image.get("height", 0),
                        hash=img_hash,
                    ))
                except Exception:
                    pass

        pdf.close()
        return doc
```

### 3.2 DOCX 解析器

```python
# backend/app/parsers/docx_parser.py
"""DOCX 解析：python-docx"""

import hashlib
from pathlib import Path

from app.models.unified_document import (
    UnifiedDocument, TextElement, ImageElement,
    TableElement, BoundingBox,
)


class DocxParser:

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        from docx import Document
        from docx.opc.constants import RELATIONSHIP_TYPE as RT

        doc = Document(str(path))
        result = UnifiedDocument(
            source_file=str(path),
            source_format="docx",
            parse_method="python-docx",
        )

        assets_dir = path.parent / "assets"
        assets_dir.mkdir(exist_ok=True)

        # 提取文字段落
        for idx, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue

            level = self._heading_level(para)
            result.texts.append(TextElement(
                id=f"docx_p{idx}",
                content=text,
                page=0,  # DOCX 无固定页面概念
                level=level,
                style=para.style.name if para.style else "Normal",
                fingerprint=hashlib.md5(text.encode()).hexdigest(),
            ))

        # 提取图片
        img_idx = 0
        for rel in doc.part.rels.values():
            if "image" not in rel.reltype:
                continue

            try:
                img_bytes = rel.target_part.blob
                ext = rel.target_part.content_type.split("/")[-1]
                if ext == "jpeg":
                    ext = "jpg"
                img_hash = hashlib.md5(img_bytes).hexdigest()[:12]

                img_path = assets_dir / f"docx_img{img_idx}_{img_hash}.{ext}"
                img_path.write_bytes(img_bytes)

                result.images.append(ImageElement(
                    id=f"docx_img{img_idx}_{img_hash}",
                    local_path=str(img_path),
                    page=0,
                    hash=img_hash,
                    alt_text="",
                ))
                img_idx += 1
            except Exception:
                result.parse_warnings.append(f"图片提取失败 rel={rel.rId}")

        # 提取表格
        for tbl_idx, table in enumerate(doc.tables):
            data = []
            for row in table.rows:
                row_data = [cell.text.strip() for cell in row.cells]
                data.append(row_data)

            result.tables.append(TableElement(
                id=f"docx_tbl{tbl_idx}",
                page=0,
                data=data,
                headers=data[0] if data else [],
            ))

        return result

    @staticmethod
    def _heading_level(paragraph) -> int:
        style_name = (paragraph.style.name or "").lower() if paragraph.style else ""
        if "heading" in style_name or "标题" in style_name:
            for i in range(1, 7):
                if str(i) in style_name:
                    return i
            return 1
        return 0
```

### 3.3 XLSX 解析器

```python
# backend/app/parsers/xlsx_parser.py
"""XLSX 解析：openpyxl + pandas"""

import hashlib
from pathlib import Path

from app.models.unified_document import (
    UnifiedDocument, TextElement, ImageElement,
    TableElement,
)


class XlsxParser:

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        import openpyxl

        wb = openpyxl.load_workbook(str(path), data_only=True)

        result = UnifiedDocument(
            source_file=str(path),
            source_format="xlsx",
            parse_method="openpyxl",
        )

        assets_dir = path.parent / "assets"
        assets_dir.mkdir(exist_ok=True)

        for sheet_name in wb.sheetnames:
            ws = wb[sheet_name]

            # 提取为表格
            data = []
            for row in ws.iter_rows(values_only=True):
                row_data = [str(cell) if cell is not None else "" for cell in row]
                # 跳过全空行
                if any(cell.strip() for cell in row_data):
                    data.append(row_data)

            if data:
                # 尝试识别表头
                headers = data[0] if data else []
                # 过滤空列
                non_empty_cols = [
                    i for i, h in enumerate(headers)
                    if h.strip()
                ]
                if non_empty_cols:
                    filtered_data = [
                        [row[i] for i in non_empty_cols if i < len(row)]
                        for row in data
                    ]
                    filtered_headers = [headers[i] for i in non_empty_cols]
                else:
                    filtered_data = data
                    filtered_headers = headers

                result.tables.append(TableElement(
                    id=f"xlsx_{sheet_name}",
                    page=0,
                    data=filtered_data,
                    headers=filtered_headers,
                ))

            # 提取工作表中的文字（标题行、注释等）
            for row_idx, row in enumerate(ws.iter_rows(max_row=1, values_only=True)):
                for col_idx, cell in enumerate(row):
                    if cell and str(cell).strip():
                        result.texts.append(TextElement(
                            id=f"xlsx_{sheet_name}_r{row_idx}c{col_idx}",
                            content=str(cell).strip(),
                            page=0,
                            level=1 if row_idx == 0 else 0,
                            fingerprint=hashlib.md5(str(cell).encode()).hexdigest(),
                        ))

            # 提取嵌入的图片
            img_idx = 0
            if hasattr(ws, "_images"):
                for img in ws._images:
                    try:
                        img_bytes = img._data()
                        img_hash = hashlib.md5(img_bytes).hexdigest()[:12]
                        img_path = assets_dir / f"xlsx_{sheet_name}_img{img_idx}_{img_hash}.png"
                        img_path.write_bytes(img_bytes)

                        result.images.append(ImageElement(
                            id=f"xlsx_{sheet_name}_img{img_idx}_{img_hash}",
                            local_path=str(img_path),
                            page=0,
                            hash=img_hash,
                        ))
                        img_idx += 1
                    except Exception:
                        pass

        wb.close()

        # 如果没有表格但有数据，创建一个默认表格
        if not result.tables and result.texts:
            result.parse_warnings.append("XLSX 未能提取到结构化表格数据")

        return result
```

### 3.4 Markdown 解析器

```python
# backend/app/parsers/md_parser.py
"""Markdown 解析：markdown-it-py"""

import hashlib
import re
from pathlib import Path

from app.models.unified_document import (
    UnifiedDocument, TextElement, ImageElement, TableElement,
)


class MdParser:

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        content = path.read_text(encoding="utf-8")

        result = UnifiedDocument(
            source_file=str(path),
            source_format="md",
            parse_method="markdown-it-py",
        )

        try:
            from markdown_it import MarkdownIt
            md = MarkdownIt("commonmark", {"html": True}).enable("table")
            tokens = md.parse(content)
        except ImportError:
            # 降级：正则解析
            return await self._parse_regex(path, content)

        text_idx = 0
        for token in tokens:
            if token.type == "heading_open":
                level = int(token.tag[1])  # h1 → 1, h2 → 2
            elif token.type == "inline":
                text = token.content.strip()
                if text:
                    # 查找最近的 heading_open 级别
                    level = 0
                    result.texts.append(TextElement(
                        id=f"md_t{text_idx}",
                        content=text,
                        page=0,
                        level=level,
                        fingerprint=hashlib.md5(text.encode()).hexdigest(),
                    ))
                    text_idx += 1

        # 提取图片引用
        img_pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
        for idx, match in enumerate(img_pattern.finditer(content)):
            alt_text = match.group(1)
            img_ref = match.group(2)

            # 解析相对路径
            img_path = path.parent / img_ref
            local_path = str(img_path) if img_path.exists() else img_ref

            img_hash = ""
            if img_path.exists():
                img_hash = hashlib.md5(img_path.read_bytes()).hexdigest()[:12]

            result.images.append(ImageElement(
                id=f"md_img{idx}",
                local_path=local_path,
                page=0,
                hash=img_hash,
                alt_text=alt_text,
            ))

        # 提取 Markdown 表格
        table_pattern = re.compile(
            r"(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n)*)", re.MULTILINE
        )
        for idx, match in enumerate(table_pattern.finditer(content)):
            lines = match.group(1).strip().split("\n")
            if len(lines) < 2:
                continue

            data = []
            for line in lines:
                cells = [c.strip() for c in line.strip("|").split("|")]
                data.append(cells)

            result.tables.append(TableElement(
                id=f"md_tbl{idx}",
                page=0,
                data=data,
                headers=data[0] if data else [],
            ))

        return result

    async def _parse_regex(self, path: Path, content: str) -> UnifiedDocument:
        """正则降级解析"""
        result = UnifiedDocument(
            source_file=str(path),
            source_format="md",
            parse_method="regex",
            parse_warnings=["降级到正则解析"],
        )

        for idx, line in enumerate(content.split("\n")):
            stripped = line.strip()
            if not stripped:
                continue

            level = 0
            if stripped.startswith("#"):
                level = len(stripped.split(" ")[0])

            # 移除 Markdown 标记
            clean = stripped.lstrip("#").strip()

            result.texts.append(TextElement(
                id=f"md_t{idx}",
                content=clean,
                page=0,
                level=level,
                fingerprint=hashlib.md5(clean.encode()).hexdigest(),
            ))

        # 图片
        for idx, match in enumerate(
            re.finditer(r"!\[([^\]]*)\]\(([^)]+)\)", content)
        ):
            result.images.append(ImageElement(
                id=f"md_img{idx}",
                local_path=match.group(2),
                page=0,
                alt_text=match.group(1),
            ))

        return result
```

---

## 四、PPT Master 集成代码

### 4.1 SVG 后处理（finalize_svg）

```python
# backend/app/exporters/ppt_master/finalize_svg.py
"""PPT Master 风格的 SVG 后处理流水线"""

import re
import base64
import hashlib
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from io import BytesIO


class SvgFinalizer:
    """SVG → PPT Master 兼容格式后处理"""

    def finalize(self, svg_content: str, assets_dir: Path) -> str:
        """完整后处理流水线"""

        soup = BeautifulSoup(svg_content, "xml")

        # 步骤 1: 嵌入图标（替换 iconify 引用）
        soup = self._embed_icons(soup, assets_dir)

        # 步骤 2: 裁剪并嵌入图片（确保宽高比正确）
        soup = self._crop_and_embed_images(soup, assets_dir)

        # 步骤 3: 修复宽高比
        soup = self._fix_aspect_ratios(soup)

        # 步骤 4: 扁平化文字（确保文字正确显示）
        soup = self._flatten_text(soup)

        # 步骤 5: 移除不兼容元素
        soup = self._remove_incompatible(soup)

        # 步骤 6: 质量检查
        svg_str = str(soup)
        self._quality_check(svg_str)

        return svg_str

    def _embed_icons(self, soup: BeautifulSoup, assets_dir: Path) -> BeautifulSoup:
        """将 iconify 图标引用替换为内联 SVG path"""

        icons_dir = assets_dir / "icons"
        if not icons_dir.exists():
            return soup

        # 加载图标库
        icon_cache = {}
        for icon_file in icons_dir.glob("*.svg"):
            icon_cache[icon_file.stem] = icon_file.read_text(encoding="utf-8")

        for elem in soup.find_all(attrs={"data-icon": True}):
            icon_name = elem.get("data-icon", "")
            if icon_name in icon_cache:
                icon_svg = BeautifulSoup(icon_cache[icon_name], "xml")
                paths = icon_svg.find_all("path")
                for path in paths:
                    # 复制到父元素
                    new_path = soup.new_tag("path")
                    new_path["d"] = path.get("d", "")
                    new_path["fill"] = elem.get("fill", "currentColor")
                    # 继承位置和大小
                    new_path["transform"] = f"translate({elem.get('x', 0)}, {elem.get('y', 0)}) scale(0.02)"
                    elem.replace_with(new_path)

        return soup

    def _crop_and_embed_images(
        self, soup: BeautifulSoup, assets_dir: Path
    ) -> BeautifulSoup:
        """裁剪图片并转为 base64 内嵌"""

        for img in soup.find_all("image"):
            href = img.get("href", "")

            # 已经是 base64 的跳过
            if href.startswith("data:"):
                continue

            # 读取本地文件
            img_path = Path(href)
            if not img_path.is_absolute():
                img_path = assets_dir / href

            if not img_path.exists():
                continue

            try:
                img_bytes = img_path.read_bytes()

                # 裁剪到目标宽高比（使用 PIL）
                target_w = int(img.get("width", 0))
                target_h = int(img.get("height", 0))
                if target_w > 0 and target_h > 0:
                    img_bytes = self._crop_to_ratio(
                        img_bytes, target_w / target_h
                    )

                # 转为 base64
                ext = img_path.suffix.lstrip(".")
                mime = {"jpg": "jpeg", "png": "png", "gif": "gif"}.get(ext, "jpeg")
                b64 = base64.b64encode(img_bytes).decode()

                img["href"] = f"data:image/{mime};base64,{b64}"
                # 移除外部引用属性
                if "xlink:href" in img.attrs:
                    del img["xlink:href"]

            except Exception:
                pass

        return soup

    def _crop_to_ratio(self, img_bytes: bytes, target_ratio: float) -> bytes:
        """裁剪图片到指定宽高比"""
        try:
            from PIL import Image

            img = Image.open(BytesIO(img_bytes))
            w, h = img.size
            current_ratio = w / h

            if abs(current_ratio - target_ratio) < 0.05:
                return img_bytes  # 宽高比已接近

            if current_ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
            else:
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))

            buf = BytesIO()
            img.save(buf, format="JPEG", quality=90)
            return buf.getvalue()
        except ImportError:
            return img_bytes

    def _fix_aspect_ratios(self, soup: BeautifulSoup) -> BeautifulSoup:
        """确保所有 image 元素设置了 preserveAspectRatio"""

        for img in soup.find_all("image"):
            if not img.get("preserveAspectRatio"):
                img["preserveAspectRatio"] = "xMidYMid slice"

        return soup

    def _flatten_text(self, soup: BeautifulSoup) -> BeautifulSoup:
        """扁平化文字元素——确保每个 <text> 只有直接文本"""

        for text_elem in soup.find_all("text"):
            # 移除 @font-face 引用，替换为通用字体
            if text_elem.get("font-family"):
                ff = text_elem["font-family"]
                # 替换不支持的字体
                safe_fonts = {
                    "Arial", "Helvetica", "Times New Roman",
                    "Georgia", "Verdana", "sans-serif", "serif",
                }
                if ff not in safe_fonts:
                    text_elem["font-family"] = "Arial"

            # 确保使用内联样式而非 CSS class
            if text_elem.get("class"):
                # 把 class 样式内联化
                del text_elem["class"]

        return soup

    def _remove_incompatible(self, soup: BeautifulSoup) -> BeautifulSoup:
        """移除 PPT Master 不兼容的 SVG 元素"""

        # 移除 mask
        for mask in soup.find_all("mask"):
            mask.decompose()
        for elem in soup.find_all(attrs={"mask": True}):
            del elem["mask"]

        # 移除 @font-face style
        for style in soup.find_all("style"):
            if "@font-face" in style.string or "":
                style.decompose()

        # 移除 CSS class 引用（转为内联）
        for elem in soup.find_all(True):
            if elem.get("class"):
                del elem["class"]

        return soup

    def _quality_check(self, svg_str: str) -> list[str]:
        """质量检查"""
        issues = []

        if "mask=" in svg_str:
            issues.append("SVG 仍包含 mask 属性")
        if "@font-face" in svg_str:
            issues.append("SVG 仍包含 @font-face")
        if 'class="' in svg_str:
            issues.append("SVG 仍包含 CSS class")
        if "viewBox" not in svg_str:
            issues.append("SVG 缺少 viewBox")

        if issues:
            raise ValueError(f"SVG 质量检查未通过: {issues}")

        return issues
```

### 4.2 SVG → PPTX 转换器

```python
# backend/app/exporters/ppt_master/svg_to_pptx.py
"""SVG → DrawingML → PPTX 转换"""

import re
import base64
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup


class SvgToPptxConverter:
    """将 PPT Master 风格的 SVG 转换为 PPTX 幻灯片"""

    EMU_PER_PX = 12700  # 1px = 12700 EMU

    def convert(
        self,
        svg_pages: list[str],
        design_spec: dict,
        output_path: Path,
        template_pptx: Path | None = None,
    ) -> Path:
        """将多个 SVG 页面转换为 PPTX"""

        from pptx import Presentation
        from pptx.util import Emu, Pt
        from pptx.enum.shapes import MSO_SHAPE_TYPE

        # 从模板或创建新的 Presentation
        if template_pptx and template_pptx.exists():
            prs = Presentation(str(template_pptx))
        else:
            prs = Presentation()
            # 设置幻灯片尺寸
            canvas_w = design_spec.get("canvas_width", 1920)
            canvas_h = design_spec.get("canvas_height", 1080)
            prs.slide_width = Emu(canvas_w * self.EMU_PER_PX)
            prs.slide_height = Emu(canvas_h * self.EMU_PER_PX)

        for svg_content in svg_pages:
            slide_layout = prs.slide_layouts[6]  # 空白布局
            slide = prs.slides.add_slide(slide_layout)

            soup = BeautifulSoup(svg_content, "xml")
            svg_root = soup.find("svg")

            if not svg_root:
                continue

            # 解析 viewBox
            viewbox = svg_root.get("viewBox", "0 0 1920 1080")
            vb_parts = viewbox.split()
            vb_w = float(vb_parts[2]) if len(vb_parts) >= 3 else 1920
            vb_h = float(vb_parts[3]) if len(vb_parts) >= 4 else 1080

            scale_x = prs.slide_width / (vb_w * self.EMU_PER_PX)
            scale_y = prs.slide_height / (vb_h * self.EMU_PER_PX)

            # 转换每个 SVG 元素
            self._convert_elements(slide, svg_root, vb_w, vb_h, prs)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(str(output_path))
        return output_path

    def _convert_elements(self, slide, svg_root, vb_w, vb_h, prs):
        """转换 SVG 子元素到 PPTX shapes"""

        for elem in svg_root.children:
            if not isinstance(elem, Tag):
                continue

            tag = elem.name

            if tag == "rect":
                self._add_rect(slide, elem, vb_w, vb_h, prs)
            elif tag == "circle" or tag == "ellipse":
                self._add_ellipse(slide, elem, vb_w, vb_h, prs)
            elif tag == "text":
                self._add_text(slide, elem, vb_w, vb_h, prs)
            elif tag == "image":
                self._add_image(slide, elem, vb_w, vb_h, prs)
            elif tag == "line":
                self._add_line(slide, elem, vb_w, vb_h, prs)

    def _svg_to_emu(self, value: float, total_svg: float, total_emu: int) -> int:
        """SVG 坐标转 EMU"""
        return int(value / total_svg * total_emu)

    def _add_rect(self, slide, elem, vb_w, vb_h, prs):
        """添加矩形"""
        from pptx.util import Emu
        from pptx.dml.color import RGBColor

        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        w = float(elem.get("width", 0))
        h = float(elem.get("height", 0))

        if w <= 0 or h <= 0:
            return

        left = self._svg_to_emu(x, vb_w, prs.slide_width)
        top = self._svg_to_emu(y, vb_h, prs.slide_height)
        width = self._svg_to_emu(w, vb_w, prs.slide_width)
        height = self._svg_to_emu(h, vb_h, prs.slide_height)

        shape = slide.shapes.add_shape(
            1,  # MSO_SHAPE.RECTANGLE
            Emu(left), Emu(top), Emu(width), Emu(height),
        )

        # 填充颜色
        fill_color = self._parse_color(elem.get("fill", ""))
        if fill_color and fill_color != "none":
            shape.fill.solid()
            try:
                shape.fill.fore_color.rgb = RGBColor.from_string(fill_color)
            except Exception:
                shape.fill.background()

        # 边框
        stroke = elem.get("stroke", "")
        if stroke and stroke != "none":
            shape.line.color.rgb = RGBColor.from_string(
                self._parse_color(stroke)
            )
        else:
            shape.line.fill.background()

    def _add_text(self, slide, elem, vb_w, vb_h, prs):
        """添加文字框"""
        from pptx.util import Emu, Pt
        from pptx.dml.color import RGBColor

        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        font_size = float(elem.get("font-size", 24))
        fill_color = self._parse_color(elem.get("fill", "#000000"))

        text_content = elem.string or ""

        # 估算文字框大小
        width = int(font_size * len(text_content) * 0.6 * self.EMU_PER_PX)
        height = int(font_size * 1.5 * self.EMU_PER_PX)

        left = self._svg_to_emu(x, vb_w, prs.slide_width)
        top = self._svg_to_emu(y, vb_h, prs.slide_height)

        txBox = slide.shapes.add_textbox(
            Emu(left), Emu(top), Emu(width), Emu(height),
        )
        tf = txBox.text_frame
        tf.word_wrap = True

        p = tf.paragraphs[0]
        p.text = text_content
        p.font.size = Pt(font_size * 0.75)  # SVG px → pt 近似

        if fill_color and fill_color != "none":
            try:
                p.font.color.rgb = RGBColor.from_string(fill_color)
            except Exception:
                pass

        font_family = elem.get("font-family", "Arial")
        if font_family:
            p.font.name = font_family.split(",")[0].strip().strip("'\"")

        # 粗体
        if elem.get("font-weight") in ("bold", "700", "800", "900"):
            p.font.bold = True

    def _add_image(self, slide, elem, vb_w, vb_h, prs):
        """添加图片"""
        from pptx.util import Emu
        import tempfile

        href = elem.get("href", elem.get("xlink:href", ""))
        if not href:
            return

        x = float(elem.get("x", 0))
        y = float(elem.get("y", 0))
        w = float(elem.get("width", 0))
        h = float(elem.get("height", 0))

        if w <= 0 or h <= 0:
            return

        # 从 base64 解码图片
        if href.startswith("data:"):
            # data:image/jpeg;base64,xxxxx
            header, data = href.split(",", 1)
            img_bytes = base64.b64decode(data)

            tmp = tempfile.NamedTemporaryFile(
                suffix=".jpg", delete=False
            )
            tmp.write(img_bytes)
            tmp.close()
            img_path = tmp.name
        else:
            img_path = href

        try:
            left = self._svg_to_emu(x, vb_w, prs.slide_width)
            top = self._svg_to_emu(y, vb_h, prs.slide_height)
            width = self._svg_to_emu(w, vb_w, prs.slide_width)
            height = self._svg_to_emu(h, vb_h, prs.slide_height)

            slide.shapes.add_picture(
                img_path,
                Emu(left), Emu(top), Emu(width), Emu(height),
            )
        except Exception:
            pass

    def _add_ellipse(self, slide, elem, vb_w, vb_h, prs):
        """添加椭圆/圆形"""
        from pptx.util import Emu
        from pptx.dml.color import RGBColor

        if elem.name == "circle":
            cx = float(elem.get("cx", 0))
            cy = float(elem.get("cy", 0))
            r = float(elem.get("r", 0))
            x, y, w, h = cx - r, cy - r, 2 * r, 2 * r
        else:  # ellipse
            cx = float(elem.get("cx", 0))
            cy = float(elem.get("cy", 0))
            rx = float(elem.get("rx", 0))
            ry = float(elem.get("ry", 0))
            x, y, w, h = cx - rx, cy - ry, 2 * rx, 2 * ry

        if w <= 0 or h <= 0:
            return

        left = self._svg_to_emu(x, vb_w, prs.slide_width)
        top = self._svg_to_emu(y, vb_h, prs.slide_height)
        width = self._svg_to_emu(w, vb_w, prs.slide_width)
        height = self._svg_to_emu(h, vb_h, prs.slide_height)

        shape = slide.shapes.add_shape(
            9,  # MSO_SHAPE.OVAL
            Emu(left), Emu(top), Emu(width), Emu(height),
        )

        fill_color = self._parse_color(elem.get("fill", ""))
        if fill_color and fill_color != "none":
            shape.fill.solid()
            try:
                opacity = elem.get("fill-opacity", "1")
                shape.fill.fore_color.rgb = RGBColor.from_string(fill_color)
            except Exception:
                shape.fill.background()
        else:
            shape.fill.background()

        shape.line.fill.background()

    def _add_line(self, slide, elem, vb_w, vb_h, prs):
        """添加线条"""
        from pptx.util import Emu

        x1 = float(elem.get("x1", 0))
        y1 = float(elem.get("y1", 0))
        x2 = float(elem.get("x2", 0))
        y2 = float(elem.get("y2", 0))

        # PPTX 中线条用 connector 表示
        left = self._svg_to_emu(min(x1, x2), vb_w, prs.slide_width)
        top = self._svg_to_emu(min(y1, y2), vb_h, prs.slide_height)
        width = self._svg_to_emu(abs(x2 - x1), vb_w, prs.slide_width)
        height = self._svg_to_emu(abs(y2 - y1), vb_h, prs.slide_height)

        # 使用自由形状线条近似
        try:
            from pptx.util import Emu as EmuType
            connector = slide.shapes.add_connector(
                1,  # straight connector
                Emu(left), Emu(top),
                Emu(left + width), Emu(top + height),
            )
            stroke_color = self._parse_color(elem.get("stroke", "#000000"))
            if stroke_color:
                from pptx.dml.color import RGBColor
                connector.line.color.rgb = RGBColor.from_string(stroke_color)
        except Exception:
            pass

    @staticmethod
    def _parse_color(color_str: str) -> str:
        """解析 SVG 颜色为 hex（不含 #）"""
        if not color_str or color_str == "none" or color_str == "transparent":
            return ""

        # 移除 # 前缀
        color_str = color_str.strip()
        if color_str.startswith("#"):
            hex_color = color_str[1:]
            if len(hex_color) == 3:
                hex_color = "".join(c * 2 for c in hex_color)
            return hex_color.upper()

        # rgb(r,g,b) 格式
        rgb_match = re.match(r"rgb\((\d+),\s*(\d+),\s*(\d+)\)", color_str)
        if rgb_match:
            return "{:02X}{:02X}{:02X}".format(
                int(rgb_match.group(1)),
                int(rgb_match.group(2)),
                int(rgb_match.group(3)),
            )

        # url(...) 引用渐变——暂不支持
        if color_str.startswith("url("):
            return ""

        return ""
```

---

## 五、混合 PDF 渲染器（Playwright + WeasyPrint）

```python
# backend/app/exporters/pdf_renderer.py
"""混合 PDF 渲染引擎：视觉页用 Playwright，文字/表格页用 WeasyPrint"""

import io
import asyncio
from pathlib import Path
from typing import Optional

from app.models.edit_actions import MagazineEditPlan
from app.models.unified_document import UnifiedDocument


class HybridPdfRenderer:
    """混合 PDF 渲染引擎"""

    # 用 Playwright 渲染的页面类型（视觉复杂）
    PLAYWRIGHT_TYPES = {"cover", "hero", "data_card", "full_image", "quote"}

    # 用 WeasyPrint 渲染的页面类型（文字/表格）
    WEASYPRINT_TYPES = {"text_only", "text_table", "text_image", "two_column"}

    async def render(
        self,
        plan: MagazineEditPlan,
        doc: UnifiedDocument,
        template_dir: Path,
        output_path: Path,
    ) -> Path:
        """完整 PDF 渲染流程"""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_pages = []

        # 加载模板
        template_dir = template_dir / plan.template_id
        template_html = (template_dir / "template.html").read_text("utf-8")
        css_content = (template_dir / "styles.css").read_text("utf-8")

        # 填充模板
        filled_pages = self._fill_template(template_html, css_content, plan, doc)

        for page_info in filled_pages:
            layout_type = page_info["layout_type"]
            page_html = page_info["html"]

            if layout_type in self.PLAYWRIGHT_TYPES:
                pdf_bytes = await self._render_playwright(page_html, css_content)
            else:
                pdf_bytes = await self._render_weasyprint(page_html, css_content)

            pdf_pages.append(pdf_bytes)

        # 合并所有页面
        self._merge_pdfs(pdf_pages, output_path)

        return output_path

    def _fill_template(
        self,
        template_html: str,
        css_content: str,
        plan: MagazineEditPlan,
        doc: UnifiedDocument,
    ) -> list[dict]:
        """将编辑动作填充到 HTML 模板"""

        from bs4 import BeautifulSoup

        pages = []

        for page_plan in plan.pages:
            soup = BeautifulSoup(template_html, "html.parser")

            # 注入 CSS
            style_tag = soup.find("style")
            if style_tag:
                style_tag.string = css_content
            else:
                style_tag = soup.new_tag("style")
                style_tag.string = css_content
                soup.head.append(style_tag)

            # 找到目标页面容器
            page_container = soup.select_one(
                f'[data-page-type="{page_plan.template_page}"]'
            )
            if not page_container:
                # 降级：使用通用容器
                page_container = soup.find("body")

            # 应用编辑动作
            for action in page_plan.actions:
                target = soup.select_one(action.target_selector)
                if not target:
                    continue

                if action.type == "replace_text":
                    # ★ 原文直接替换
                    target.string = action.content

                elif action.type == "replace_image":
                    img = next(
                        (i for i in doc.images if i.id == action.source_id), None
                    )
                    if img:
                        target["src"] = img.local_path
                        # 确保图片不超出容器
                        target["style"] = "max-width: 100%; height: auto;"

                elif action.type == "replace_table_data":
                    tbl = next(
                        (t for t in doc.tables if t.id == action.source_id), None
                    )
                    if tbl:
                        table_html = self._build_table_html(tbl.data, tbl.headers)
                        target.replace_with(
                            BeautifulSoup(table_html, "html.parser")
                        )

            pages.append({
                "layout_type": page_plan.template_page,
                "html": str(soup),
            })

        return pages

    def _build_table_html(
        self, data: list[list[str]], headers: list[str]
    ) -> str:
        """构建 HTML 表格"""
        parts = ['<table class="data-table">']

        if headers:
            parts.append("<thead><tr>")
            for h in headers:
                parts.append(f"<th>{_escape_html(h)}</th>")
            parts.append("</tr></thead>")

        parts.append("<tbody>")
        for row in data:
            parts.append("<tr>")
            for cell in row:
                parts.append(f"<td>{_escape_html(cell)}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

        return "".join(parts)

    async def _render_playwright(
        self, html: str, css: str
    ) -> bytes:
        """Playwright 渲染（适合视觉复杂页）"""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            await page.set_content(html, wait_until="networkidle")

            # 注入额外 CSS 确保分页
            await page.add_style_tag(content=f"""
                {css}
                @page {{ size: A4; margin: 0; }}
                body {{ margin: 0; }}
            """)

            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
            )

            await browser.close()
            return pdf_bytes

    async def _render_weasyprint(
        self, html: str, css: str
    ) -> bytes:
        """WeasyPrint 渲染（适合文字/表格页，正确分页）"""
        from weasyprint import HTML, CSS

        # 注入表格分页 CSS
        table_css = css + """
        table { page-break-inside: auto; }
        tr    { page-break-inside: avoid; page-break-after: auto; }
        td    { page-break-inside: avoid; }
        thead { display: table-header-group; }
        tfoot { display: table-footer-group; }
        """

        html_doc = HTML(string=html)
        css_doc = CSS(string=table_css)

        pdf_bytes = html_doc.write_pdf(stylesheets=[css_doc])
        return pdf_bytes

    def _merge_pdfs(self, pdf_pages: list[bytes], output_path: Path) -> None:
        """合并多个 PDF 页面"""
        from PyPDF2 import PdfMerger

        merger = PdfMerger()
        for pdf_bytes in pdf_pages:
            merger.append(io.BytesIO(pdf_bytes))

        merger.write(str(output_path))
        merger.close()


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
```

---

## 六、更新后的 Parser Agent（整合所有解析器）

```python
# backend/app/agents/parser_agent.py
"""完整版 Parser Agent：整合所有格式解析器"""

from pathlib import Path
from app.models.unified_document import (
    UnifiedDocument, ContentAssetLink, BoundingBox,
)


class ParserAgent:
    """按文件类型选择最佳解析器，输出统一格式"""

    def __init__(self):
        self._parsers = {}

    def _get_parsers(self):
        """延迟加载解析器（避免 import 循环）"""
        if not self._parsers:
            from app.parsers.pptx_parser import PptxParser
            from app.parsers.pdf_parser import PdfParser
            from app.parsers.docx_parser import DocxParser
            from app.parsers.xlsx_parser import XlsxParser
            from app.parsers.md_parser import MdParser

            self._parsers = {
                ".pptx": PptxParser(),
                ".pdf": PdfParser(),
                ".docx": DocxParser(),
                ".xlsx": XlsxParser(),
                ".md": MdParser(),
                ".txt": MdParser(),  # Markdown 解析器也能处理纯文本
            }
        return self._parsers

    async def parse(self, file_path: Path, session_id: str) -> UnifiedDocument:
        ext = file_path.suffix.lower()
        parsers = self._get_parsers()

        parser = parsers.get(ext)
        if not parser:
            raise ValueError(
                f"不支持的格式: {ext}。"
                f"支持: {', '.join(parsers.keys())}"
            )

        doc = await parser.parse(file_path, session_id)

        # 构建图文关联
        doc.linkage = self._build_linkage(doc)

        # 设置元信息
        doc.source_file = str(file_path)
        doc.source_format = ext.lstrip(".")

        return doc

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
                    if dist < 500000:
                        links.append(ContentAssetLink(
                            text_id=text.id,
                            asset_id=img.id,
                            asset_type="image",
                            strategy="spatial",
                            confidence=max(0, 1 - dist / 500000),
                        ))

                # 策略2: 结构关键词
                if any(kw in text.content for kw in ["图", "注", "见图", "如图", "图片", "图示"]):
                    links.append(ContentAssetLink(
                        text_id=text.id,
                        asset_id=img.id,
                        asset_type="image",
                        strategy="structural",
                        confidence=0.7,
                    ))

            # 文字-表格关联
            for tbl in doc.tables:
                if text.page != tbl.page:
                    continue
                if any(kw in text.content for kw in ["表", "数据", "如下", "见表", "表格"]):
                    links.append(ContentAssetLink(
                        text_id=text.id,
                        asset_id=tbl.id,
                        asset_type="table",
                        strategy="structural",
                        confidence=0.6,
                    ))

        # 策略3: 语义关联（由 Analyzer Agent 补充）
        return links

    @staticmethod
    def _bbox_distance(a: BoundingBox, b: BoundingBox) -> float:
        import math
        ca = (a.left + a.width / 2, a.top + a.height / 2)
        cb = (b.left + b.width / 2, b.top + b.height / 2)
        return math.sqrt((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2)
```

### 补充：PPTX 独立解析器

```python
# backend/app/parsers/pptx_parser.py
"""PPTX 解析：python-pptx 直接解析（最稳定路径）"""

import hashlib
from pathlib import Path

from app.models.unified_document import (
    UnifiedDocument, TextElement, ImageElement,
    TableElement, BoundingBox,
)


class PptxParser:

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        from pptx import Presentation

        prs = Presentation(str(path))

        doc = UnifiedDocument(
            source_file=str(path),
            source_format="pptx",
            parse_method="python-pptx",
            total_pages=len(prs.slides),
        )

        assets_dir = path.parent / "assets"
        assets_dir.mkdir(exist_ok=True)

        for slide_idx, slide in enumerate(prs.slides):
            for shape in slide.shapes:

                # 文字
                if shape.has_text_frame:
                    for para_idx, para in enumerate(shape.text_frame.paragraphs):
                        text = para.text.strip()
                        if not text:
                            continue

                        doc.texts.append(TextElement(
                            id=f"s{slide_idx}_sh{shape.shape_id}_p{para_idx}",
                            content=text,
                            page=slide_idx,
                            bbox=BoundingBox(
                                left=shape.left,
                                top=shape.top,
                                width=shape.width,
                                height=shape.height,
                            ),
                            level=para.level,
                            fingerprint=hashlib.md5(text.encode()).hexdigest(),
                        ))

                # 图片（shape_type == 13 = PICTURE）
                if shape.shape_type == 13:
                    try:
                        img_bytes = shape.image.blob
                        content_type = shape.image.content_type
                        ext = content_type.split("/")[-1]
                        if ext == "jpeg":
                            ext = "jpg"

                        img_hash = hashlib.md5(img_bytes).hexdigest()[:12]
                        img_path = assets_dir / f"s{slide_idx}_sh{shape.shape_id}_{img_hash}.{ext}"
                        img_path.write_bytes(img_bytes)

                        doc.images.append(ImageElement(
                            id=f"s{slide_idx}_img_{img_hash}",
                            local_path=str(img_path),
                            page=slide_idx,
                            bbox=BoundingBox(
                                left=shape.left,
                                top=shape.top,
                                width=shape.width,
                                height=shape.height,
                            ),
                            width=shape.width,
                            height=shape.height,
                            hash=img_hash,
                        ))
                    except Exception:
                        doc.parse_warnings.append(
                            f"Slide {slide_idx}: 图片提取失败 shape={shape.shape_id}"
                        )

                # 表格
                if shape.has_table:
                    data = [
                        [cell.text for cell in row.cells]
                        for row in shape.table.rows
                    ]
                    doc.tables.append(TableElement(
                        id=f"s{slide_idx}_tbl_{shape.shape_id}",
                        page=slide_idx,
                        bbox=BoundingBox(
                            left=shape.left,
                            top=shape.top,
                            width=shape.width,
                            height=shape.height,
                        ),
                        data=data,
                        headers=data[0] if data else [],
                    ))

                # 图表（从图表中提取数据表）
                if shape.has_chart:
                    try:
                        chart = shape.chart
                        chart_data = []
                        for series in chart.series:
                            values = [str(v) for v in series.values]
                            chart_data.append(values)

                        if chart_data:
                            doc.tables.append(TableElement(
                                id=f"s{slide_idx}_chart_{shape.shape_id}",
                                page=slide_idx,
                                bbox=BoundingBox(
                                    left=shape.left,
                                    top=shape.top,
                                    width=shape.width,
                                    height=shape.height,
                                ),
                                data=chart_data,
                                is_chart=True,
                            ))
                    except Exception:
                        doc.parse_warnings.append(
                            f"Slide {slide_idx}: 图表提取失败 shape={shape.shape_id}"
                        )

        return doc
```

---

## 七、完整的配置管理

```python
# backend/app/core/config.py
"""V4 架构配置管理"""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    """全局配置（从环境变量加载）"""

    # ---- Presenton 原有 ----
    APP_NAME: str = "Magazine Document Agent"
    DEBUG: bool = False

    # 数据库
    DATABASE_URL: str = "sqlite:///./app_data/magazine.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # 文件存储
    UPLOAD_DIR: str = "./data/uploads"
    OUTPUT_DIR: str = "./data/output"
    ASSETS_DIR: str = "./data/assets"
    TEMPLATE_DIR: str = "./app/templates"

    # ---- GLM-5 API 配置 ----
    LLM: str = "custom"
    CUSTOM_LLM_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    CUSTOM_MODEL: str = "glm-5-pro"
    CUSTOM_LLM_API_KEY: str = ""

    # ---- 素材补充 ----
    IMAGE_PROVIDER: str = "pexels"
    PEXELS_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

    # ---- 保真校验 ----
    FIDELITY_THRESHOLD: float = 0.95
    MAX_REPAIR_ATTEMPTS: int = 2

    # ---- Docling ----
    DOCILING_TIMEOUT: int = 300

    # ---- Playwright ----
    PLAYWRIGHT_HEADLESS: bool = True

    # ---- 模板 ----
    MAGAZINE_TEMPLATES_DIR: str = "./app/templates"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
```

---

## 八、LangGraph 工作流完整版本

```python
# backend/app/workflow/magazine_pipeline.py
"""完整 LangGraph 工作流——包含所有节点实现"""

import asyncio
from typing import TypedDict
from pathlib import Path

from langgraph.graph import StateGraph, END

from app.models.unified_document import UnifiedDocument
from app.models.edit_actions import MagazineEditPlan
from app.models.design_spec import DesignSpec


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

    # Supplementer Agent 输出
    supplemented: bool

    # Renderer Agent 输出
    output_path: str

    # Fidelity Agent 输出
    fidelity_score: float
    fidelity_passed: bool
    fidelity_issues: list[dict]
    repair_count: int


async def _get_api_key(session_id: str) -> str:
    """从 Redis 获取用户的 API Key"""
    from app.core.redis import redis_client
    from cryptography.fernet import Fernet

    redis = redis_client.client
    encrypted = await redis.hget(f"api_keys:{session_id}", "zhipu_key")
    if not encrypted:
        raise ValueError("未配置智谱 API Key，请先在设置中配置")
    return encrypted.decode() if isinstance(encrypted, bytes) else encrypted


# ---- 节点实现 ----

async def parser_node(state: PipelineState) -> dict:
    from app.agents.parser_agent import ParserAgent
    agent = ParserAgent()
    doc = await agent.parse(Path(state["file_path"]), state["session_id"])
    return {
        "document": doc,
        "parse_warnings": doc.parse_warnings,
    }


async def analyzer_node(state: PipelineState) -> dict:
    from app.agents.analyzer_agent import AnalyzerAgent
    api_key = await _get_api_key(state["session_id"])
    agent = AnalyzerAgent(api_key)
    analysis = await agent.analyze(state["document"])
    return {"analysis": analysis}


async def designer_node(state: PipelineState) -> dict:
    from app.agents.designer_agent import DesignerAgent
    api_key = await _get_api_key(state["session_id"])
    agent = DesignerAgent(api_key)
    plan = await agent.design(
        state["document"],
        state["analysis"],
        state["template_id"],
    )
    return {
        "edit_plan": plan,
        "design_spec": plan.design_spec,
    }


async def check_missing_assets_node(state: PipelineState) -> str:
    """条件路由：检查是否有缺失素材"""
    plan = state["edit_plan"]
    doc = state["document"]

    for page in plan.pages:
        for action in page.actions:
            if action.type == "replace_image":
                img = next(
                    (i for i in doc.images if i.id == action.source_id), None
                )
                if not img or not Path(img.local_path).exists():
                    return "supplement"

    return "render"


async def supplement_node(state: PipelineState) -> dict:
    from app.agents.supplement_agent import SupplementAgent
    agent = SupplementAgent(state["session_id"])
    await agent.supplement(state["document"], state["edit_plan"])
    return {"supplemented": True}


async def renderer_node(state: PipelineState) -> dict:
    from app.agents.renderer_agent import RendererAgent
    from app.core.config import settings

    agent = RendererAgent()
    template_dir = Path(settings.MAGAZINE_TEMPLATES_DIR)
    output_dir = Path(settings.OUTPUT_DIR) / state["session_id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    if state["output_format"] == "pdf":
        output_path = output_dir / "magazine.pdf"
        path = await agent.render_pdf(
            state["edit_plan"],
            state["document"],
            template_dir / "pdf",
            output_path,
        )
    else:
        output_path = output_dir / "magazine.pptx"
        path = await agent.render_pptx(
            state["edit_plan"],
            state["document"],
            template_dir / "pptx",
            output_path,
        )

    return {"output_path": str(path)}


async def fidelity_node(state: PipelineState) -> dict:
    from app.agents.fidelity_agent import FidelityAgent
    from app.core.config import settings

    api_key = await _get_api_key(state["session_id"])
    agent = FidelityAgent(
        api_key,
        threshold=settings.FIDELITY_THRESHOLD,
    )
    result = await agent.verify(state["document"], state["edit_plan"])
    return {
        "fidelity_score": result.overall_score,
        "fidelity_passed": result.passed,
        "fidelity_issues": [i.dict() for i in result.issues],
    }


async def repair_node(state: PipelineState) -> dict:
    """自动修复遗漏内容"""
    from app.models.edit_actions import EditAction, SlideEditPlan

    repair_count = state.get("repair_count", 0) + 1
    plan = state["edit_plan"]
    doc = state["document"]

    for issue in state.get("fidelity_issues", []):
        if issue.get("category") != "fingerprint":
            continue

        if "遗漏" in issue.get("description", ""):
            element_id = issue.get("element_id", "")

            # 找到遗漏的元素
            text = next((t for t in doc.texts if t.id == element_id), None)
            if text:
                # 追加到最后一页或新建一页
                if plan.pages:
                    target_page = plan.pages[-1]
                else:
                    target_page = SlideEditPlan(
                        page_number=1,
                        template_page="text_only",
                    )
                    plan.pages.append(target_page)

                target_page.actions.append(EditAction(
                    type="replace_text",
                    target_selector=f".repaired-{len(target_page.actions)}",
                    source_id=text.id,
                    content=text.content,
                ))

    return {
        "edit_plan": plan,
        "repair_count": repair_count,
    }


async def finalize_node(state: PipelineState) -> dict:
    """最终节点：记录完成状态"""
    from app.core.config import settings
    import json

    summary = {
        "output_path": state.get("output_path", ""),
        "fidelity_score": state.get("fidelity_score", 0),
        "fidelity_passed": state.get("fidelity_passed", False),
        "repair_count": state.get("repair_count", 0),
        "supplemented": state.get("supplemented", False),
    }

    # 保存任务完成记录
    output_dir = Path(settings.OUTPUT_DIR) / state["session_id"]
    summary_path = output_dir / "task_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {}


def should_repair(state: PipelineState) -> str:
    """条件路由：保真校验是否通过"""
    if not state.get("fidelity_passed", False) and state.get("repair_count", 0) < 2:
        return "repair"
    return "finalize"


def build_magazine_pipeline():
    """构建完整的 LangGraph 工作流"""
    graph = StateGraph(PipelineState)

    # 注册所有节点
    graph.add_node("parse", parser_node)
    graph.add_node("analyze", analyzer_node)
    graph.add_node("design", designer_node)
    graph.add_node("supplement", supplement_node)
    graph.add_node("render", renderer_node)
    graph.add_node("verify", fidelity_node)
    graph.add_node("repair", repair_node)
    graph.add_node("finalize", finalize_node)

    # 定义流程
    graph.set_entry_point("parse")
    graph.add_edge("parse", "analyze")
    graph.add_edge("analyze", "design")

    # 条件: 是否需要补充素材
    graph.add_conditional_edges(
        "design",
        check_missing_assets_node,
        {"supplement": "supplement", "render": "render"},
    )

    graph.add_edge("supplement", "render")
    graph.add_edge("render", "verify")

    # 条件: 保真校验是否通过
    graph.add_conditional_edges(
        "verify",
        should_repair,
        {"repair": "repair", "finalize": "finalize"},
    )

    graph.add_edge("repair", "verify")
    graph.add_edge("finalize", END)

    return graph.compile()
```

---

## 九、API 路由完整实现

```python
# backend/app/api/v1/magazine.py
"""杂志级文档重构 API 完整实现"""

import uuid
import json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter(prefix="/magazine", tags=["Magazine"])


class GenerateRequest(BaseModel):
    task_id: str
    session_id: str
    output_format: str = "pdf"     # pdf | pptx
    template_id: str = "modern_tech"


class TaskStatus(BaseModel):
    task_id: str
    status: str       # pending | parsing | analyzing | designing | rendering | verifying | completed | failed
    progress: float
    message: str = ""
    fidelity_score: float | None = None
    output_path: str | None = None


# 内存任务存储（生产环境替换为 Redis/DB）
_tasks: dict[str, TaskStatus] = {}


def _get_task_dir(task_id: str) -> Path:
    return Path(settings.OUTPUT_DIR) / task_id


@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """上传文件并启动完整处理流程"""

    allowed = {".pptx", ".pdf", ".docx", ".xlsx", ".md", ".txt"}
    ext = Path(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"不支持的格式: {ext}")

    task_id = str(uuid.uuid4())
    task_dir = _get_task_dir(task_id)
    task_dir.mkdir(parents=True, exist_ok=True)

    # 保存上传文件
    file_path = task_dir / f"source{ext}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    _tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        progress=0.0,
    )

    background_tasks.add_task(_run_pipeline, task_id, file_path)

    return {"task_id": task_id, "status": "pending"}


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


@router.get("/fidelity/{task_id}")
async def get_fidelity_report(task_id: str):
    task_dir = _get_task_dir(task_id)
    report_path = task_dir / "task_summary.json"
    if not report_path.exists():
        raise HTTPException(404, "保真报告尚未生成")

    return json.loads(report_path.read_text("utf-8"))


@router.get("/export/{task_id}")
async def export_file(task_id: str, format: str = "pdf"):
    task = _tasks.get(task_id)
    if not task or task.status != "completed":
        raise HTTPException(400, "文件尚未生成完成")

    task_dir = _get_task_dir(task_id)
    ext = "pdf" if format == "pdf" else "pptx"
    file_path = task_dir / f"magazine.{ext}"

    if not file_path.exists():
        raise HTTPException(404, "输出文件不存在")

    media_type = "application/pdf" if ext == "pdf" else (
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=f"magazine_{task_id[:8]}.{ext}",
    )


# ---- 后台任务 ----

async def _run_pipeline(task_id: str, file_path: Path):
    """后台运行完整 LangGraph 工作流"""
    from app.workflow.magazine_pipeline import build_magazine_pipeline

    task = _tasks[task_id]

    try:
        pipeline = build_magazine_pipeline()

        # 按步骤更新进度
        task.status = "parsing"
        task.progress = 0.1

        result = await pipeline.ainvoke({
            "file_path": str(file_path),
            "session_id": task_id,
            "output_format": "pdf",
            "template_id": "modern_tech",
            "repair_count": 0,
        })

        task.status = "completed"
        task.progress = 1.0
        task.output_path = result.get("output_path", "")
        task.fidelity_score = result.get("fidelity_score", 0)

    except Exception as e:
        task.status = "failed"
        task.message = str(e)[:500]
```

---

## 十、最终文件结构总览

```
doc-magazine-agent/                          # 基于 Presenton fork
├── docker-compose.yml                       # 4 个服务（V4 精简版）
├── Dockerfile                               # 后端镜像
├── .env.example                             # 环境变量模板
│
├── backend/
│   ├── requirements.txt                     # Python 依赖
│   └── app/
│       ├── main.py                          # FastAPI 入口（Presenton 原有）
│       ├── core/
│       │   ├── config.py                    # ★ V4 配置管理
│       │   └── redis.py                     # Redis 客户端
│       ├── api/v1/
│       │   ├── auth.py                      # Presenton 原有
│       │   ├── ppt.py                       # Presenton 原有
│       │   └── magazine.py                  # ★ 杂志重构 API
│       ├── models/
│       │   ├── unified_document.py          # ★ 统一文档模型
│       │   ├── edit_actions.py              # ★ 编辑动作模型
│       │   └── design_spec.py               # ★ 设计规范模型
│       ├── agents/                          # ★ 五个智能体
│       │   ├── parser_agent.py              #   解析路由
│       │   ├── analyzer_agent.py            #   内容分析
│       │   ├── designer_agent.py            #   排版设计
│       │   ├── renderer_agent.py            #   渲染路由
│       │   ├── fidelity_agent.py            #   保真校验
│       │   └── supplement_agent.py          #   素材补充
│       ├── parsers/                         # ★ 多格式解析器
│       │   ├── pptx_parser.py               #   python-pptx
│       │   ├── pdf_parser.py                #   Docling + PyMuPDF
│       │   ├── docx_parser.py               #   python-docx
│       │   ├── xlsx_parser.py               #   openpyxl
│       │   └── md_parser.py                 #   markdown-it-py
│       ├── exporters/                       # ★ 渲染引擎
│       │   ├── ppt_master/
│       │   │   ├── svg_to_pptx.py           #   SVG → DrawingML 转换
│       │   │   └── finalize_svg.py          #   SVG 后处理流水线
│       │   └── pdf_renderer.py              #   Playwright + WeasyPrint
│       ├── workflow/
│       │   └── magazine_pipeline.py         # ★ LangGraph 工作流
│       └── templates/                       # ★ 杂志模板库
│           ├── pdf/
│           │   └── modern_tech/
│           │       ├── template.html
│           │       ├── styles.css
│           │       └── config.json
│           └── pptx/
│               └── modern_tech/
│                   ├── template.pptx
│                   ├── pages/
│                   │   ├── cover.svg
│                   │   ├── content_text.svg
│                   │   ├── content_image_text.svg
│                   │   └── data_card.svg
│                   └── config.json
│
└── frontend/                                # Presenton 前端 + 改造
    └── src/
        ├── app/magazine/                    # ★ 新增页面
        └── components/FidelityReport/       # ★ 新增组件
```
