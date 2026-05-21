"""Parser Agent — 文件类型路由 → 调用对应解析器 → 输出 UnifiedDocument"""
import math
from pathlib import Path

from app.models.unified_document import (
    UnifiedDocument, ContentAssetLink, BoundingBox,
)


class ParserAgent:
    """按文件类型选择最佳解析器，输出统一格式"""

    def __init__(self):
        self._parsers: dict = {}

    def _get_parsers(self) -> dict:
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
                ".txt": MdParser(),
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

        # 尝试从缓存获取
        from app.core.cache import ParseCache
        cached = await ParseCache.get(file_path)
        if cached:
            cached.linkage = self._build_linkage(cached)
            return cached

        doc = await parser.parse(file_path, session_id)
        doc.linkage = self._build_linkage(doc)
        doc.source_file = str(file_path)
        doc.source_format = ext.lstrip(".")

        # 写入缓存
        await ParseCache.set(file_path, doc)

        return doc

    def _build_linkage(self, doc: UnifiedDocument) -> list[ContentAssetLink]:
        links: list[ContentAssetLink] = []

        for text in doc.texts:
            for img in doc.images:
                if text.page != img.page:
                    continue

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

                if any(kw in text.content for kw in ["图", "注", "见图", "如图", "图片", "图示"]):
                    links.append(ContentAssetLink(
                        text_id=text.id,
                        asset_id=img.id,
                        asset_type="image",
                        strategy="structural",
                        confidence=0.7,
                    ))

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

        return links

    @staticmethod
    def _bbox_distance(a: BoundingBox, b: BoundingBox) -> float:
        ca = (a.left + a.width / 2, a.top + a.height / 2)
        cb = (b.left + b.width / 2, b.top + b.height / 2)
        return math.sqrt((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2)
