import asyncio
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from app.models.unified_document import (
    UnifiedDocument,
    TextElement,
    ImageElement,
    TableElement,
    BoundingBox,
)


class PdfParser:
    def __init__(self):
        self._session_id = ""
        self._assets_dir: Path | None = None

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        self._session_id = session_id
        self._assets_dir = path.parent / "assets" / session_id
        self._assets_dir.mkdir(parents=True, exist_ok=True)

        try:
            return await self._parse_with_docling(path)
        except Exception as e:
            warning = f"Docling解析失败: {e}，降级到PyMuPDF"
            return await self._parse_with_pymupdf(path, [warning])

    async def _parse_with_docling(self, path: Path) -> UnifiedDocument:
        script_content = f"""
import json
import sys
from pathlib import Path

try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(format_options={{
        InputFormat.PDF: pipeline_options
    }})

    doc = converter.convert(str(Path(r"{path}")))

    result = {{
        "pages": doc.pages_count,
        "texts": [],
        "tables": []
    }}

    for page in doc.pages:
        for element in page.elements:
            if hasattr(element, "text") and element.text:
                result["texts"].append({{
                    "content": element.text,
                    "page": page.page_no + 1,
                    "bbox": {{
                        "left": int(element.prov[0].bbox.l * 12700) if hasattr(element, "prov") and element.prov else 0,
                        "top": int(element.prov[0].bbox.t * 12700) if hasattr(element, "prov") and element.prov else 0,
                        "width": int(element.prov[0].bbox.w * 12700) if hasattr(element, "prov") and element.prov else 0,
                        "height": int(element.prov[0].bbox.h * 12700) if hasattr(element, "prov") and element.prov else 0
                    }},
                    "level": 0
                }})
            elif hasattr(element, "tables"):
                for table in element.tables:
                    table_data = []
                    for row in table.table.rows:
                        table_data.append([cell.text for cell in row.cells])
                    result["tables"].append({{
                        "data": table_data,
                        "page": page.page_no + 1,
                        "bbox": {{
                            "left": 0,
                            "top": 0,
                            "width": 0,
                            "height": 0
                        }}
                    }})

    print(json.dumps(result))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
    sys.exit(1)
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", encoding="utf-8", delete=False
        ) as f:
            f.write(script_content)
            script_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                script_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=300.0
            )

            if proc.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="ignore") if stderr else "未知错误"
                raise RuntimeError(f"Docling子进程失败: {error_msg}")

            result = json.loads(stdout.decode("utf-8"))
            if "error" in result:
                raise RuntimeError(f"Docling解析错误: {result['error']}")

            doc = UnifiedDocument(
                source_file=str(path),
                source_format="pdf",
                parse_method="docling",
                parse_warnings=[],
                total_pages=result["pages"],
            )

            text_idx = 0
            for text_data in result["texts"]:
                text_idx += 1
                element_id = f"pdf_p{text_data['page']}_t{text_idx}"
                fingerprint = hashlib.md5(
                    text_data["content"].encode("utf-8")
                ).hexdigest()

                doc.texts.append(
                    TextElement(
                        id=element_id,
                        content=text_data["content"],
                        page=text_data["page"],
                        bbox=BoundingBox(**text_data["bbox"]),
                        level=text_data.get("level", 0),
                        fingerprint=fingerprint,
                    )
                )

            table_idx = 0
            for table_data in result["tables"]:
                table_idx += 1
                element_id = f"pdf_p{table_data['page']}_tbl{table_idx}"

                doc.tables.append(
                    TableElement(
                        id=element_id,
                        page=table_data["page"],
                        bbox=BoundingBox(**table_data["bbox"]),
                        data=table_data["data"],
                        headers=table_data["data"][0] if table_data["data"] else [],
                    )
                )

            await self._extract_images_with_pymupdf(path, doc)

            return doc

        finally:
            Path(script_path).unlink(missing_ok=True)

    async def _parse_with_pymupdf(
        self, path: Path, extra_warnings: list[str]
    ) -> UnifiedDocument:
        import fitz

        pdf = fitz.open(str(path))
        doc = UnifiedDocument(
            source_file=str(path),
            source_format="pdf",
            parse_method="pymupdf",
            parse_warnings=extra_warnings.copy(),
            total_pages=len(pdf),
        )

        for page_idx, page in enumerate(pdf, start=1):
            page_dict = page.get_text("dict")
            text_idx = 0

            for block in page_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if not span["text"].strip():
                                continue

                            text_idx += 1
                            element_id = f"pdf_p{page_idx}_t{text_idx}"
                            fingerprint = hashlib.md5(
                                span["text"].encode("utf-8")
                            ).hexdigest()

                            level = 0
                            if span["size"] > 20:
                                level = 1
                            elif span["size"] > 16:
                                level = 2

                            bbox = BoundingBox(
                                left=int(span["bbox"][0] * 12700),
                                top=int(span["bbox"][1] * 12700),
                                width=int(span["bbox"][2] - span["bbox"][0]) * 12700,
                                height=int(span["bbox"][3] - span["bbox"][1]) * 12700,
                            )

                            doc.texts.append(
                                TextElement(
                                    id=element_id,
                                    content=span["text"],
                                    page=page_idx,
                                    bbox=bbox,
                                    level=level,
                                    style=span["font"],
                                    fingerprint=fingerprint,
                                )
                            )

            await self._extract_images_from_page(pdf, page, page_idx, doc)

        pdf.close()

        return doc

    async def _extract_images_with_pymupdf(
        self, path: Path, doc: UnifiedDocument
    ):
        import fitz

        pdf = fitz.open(str(path))
        image_idx = 0

        for page_idx, page in enumerate(pdf, start=1):
            await self._extract_images_from_page(pdf, page, page_idx, doc)

        pdf.close()

    async def _extract_images_from_page(
        self, pdf: Any, page: Any, page_idx: int, doc: UnifiedDocument
    ):
        image_list = page.get_images(full=True)
        image_idx = len([img for img in doc.images if img.page == page_idx])

        for img_info in image_list:
            xref = img_info[0]
            base_image = pdf.extract_image(xref)

            if not base_image:
                continue

            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_hash = hashlib.md5(image_bytes).hexdigest()
            image_idx += 1

            filename = f"pdf_p{page_idx}_img{image_idx}.{image_ext}"
            image_path = self._assets_dir / filename
            image_path.write_bytes(image_bytes)

            image_rects = page.get_image_rects(xref)
            bbox = None

            if image_rects:
                rect = image_rects[0]
                bbox = BoundingBox(
                    left=int(rect.x0 * 12700),
                    top=int(rect.y0 * 12700),
                    width=int(rect.width * 12700),
                    height=int(rect.height * 12700),
                )

            doc.images.append(
                ImageElement(
                    id=f"pdf_p{page_idx}_img{image_idx}",
                    local_path=str(image_path),
                    page=page_idx,
                    bbox=bbox,
                    hash=image_hash,
                )
            )