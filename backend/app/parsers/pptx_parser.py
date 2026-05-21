import asyncio
import hashlib
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.shapes.autoshape import Shape
from pptx.shapes.graphfrm import GraphicFrame
from pptx.enum.shapes import MSO_SHAPE_TYPE

from app.models.unified_document import (
    UnifiedDocument,
    TextElement,
    ImageElement,
    TableElement,
    BoundingBox,
)


class PptxParser:
    def __init__(self):
        self._session_id = ""
        self._assets_dir: Path | None = None

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        self._session_id = session_id
        self._assets_dir = path.parent / "assets" / session_id
        self._assets_dir.mkdir(parents=True, exist_ok=True)

        prs = Presentation(str(path))

        elements = []
        for slide_idx, slide in enumerate(prs.slides):
            for shape in slide.shapes:
                try:
                    shape_elements = await self._parse_shape(
                        shape, slide_idx, path
                    )
                    elements.extend(shape_elements)
                except Exception as e:
                    UnifiedDocument.parse_warnings.append(
                        f"Slide {slide_idx} Shape {shape.shape_id} parse error: {e}"
                    )

        return UnifiedDocument(
            source_format="pptx",
            parse_method="python-pptx",
            elements=elements,
            metadata={
                "total_slides": len(prs.slides),
                "total_elements": len(elements),
                "session_id": session_id,
            },
        )

    async def _parse_shape(
        self, shape: Shape | GraphicFrame, slide_idx: int, file_path: Path
    ) -> list[TextElement | ImageElement | TableElement]:
        bbox = BoundingBox(
            left=shape.left,
            top=shape.top,
            width=shape.width,
            height=shape.height,
        )

        if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
            return await self._parse_image(shape, slide_idx, bbox)
        elif hasattr(shape, "has_table") and shape.has_table:
            return await self._parse_table(shape, slide_idx, bbox)
        elif hasattr(shape, "has_chart") and shape.has_chart:
            return await self._parse_chart(shape, slide_idx, bbox)
        elif hasattr(shape, "has_text_frame") and shape.has_text_frame:
            return await self._parse_text(shape, slide_idx, bbox)
        else:
            return []

    async def _parse_text(
        self, shape: Shape, slide_idx: int, bbox: BoundingBox
    ) -> list[TextElement]:
        elements = []
        text_frame = shape.text_frame

        for para_idx, paragraph in enumerate(text_frame.paragraphs):
            if not paragraph.text.strip():
                continue

            fingerprint = hashlib.md5(
                paragraph.text.encode("utf-8")
            ).hexdigest()
            element_id = f"s{slide_idx}_sh{shape.shape_id}_p{para_idx}"

            elements.append(
                TextElement(
                    id=element_id,
                    text=paragraph.text,
                    bbox=bbox,
                    fingerprint=fingerprint,
                    level=paragraph.level,
                    font_name=paragraph.fonts[0].name if paragraph.fonts else None,
                    font_size=paragraph.fonts[0].size if paragraph.fonts else None,
                    is_bold=paragraph.fonts[0].bold if paragraph.fonts else False,
                    is_italic=paragraph.fonts[0].italic if paragraph.fonts else False,
                )
            )

        return elements

    async def _parse_image(
        self, shape: Shape, slide_idx: int, bbox: BoundingBox
    ) -> list[ImageElement]:
        image_stream = shape.image.blob
        image_hash = hashlib.md5(image_stream).hexdigest()
        image_ext = shape.image.ext
        filename = f"s{slide_idx}_sh{shape.shape_id}.{image_ext}"
        image_path = self._assets_dir / filename

        image_path.write_bytes(image_stream)

        return [
            ImageElement(
                id=f"s{slide_idx}_sh{shape.shape_id}",
                bbox=bbox,
                hash=image_hash,
                path=str(image_path.relative_to(image_path.parent.parent.parent)),
                alt_text=shape.alt_text or None,
            )
        ]

    async def _parse_table(
        self, shape: GraphicFrame, slide_idx: int, bbox: BoundingBox
    ) -> list[TableElement]:
        table = shape.table
        headers = None
        data = []

        for row_idx, row in enumerate(table.rows):
            row_data = []
            for cell in row.cells:
                row_data.append(cell.text.strip())

            if row_idx == 0:
                headers = row_data
            else:
                data.append(row_data)

        table_hash = hashlib.md5(
            str(headers + data).encode("utf-8")
        ).hexdigest()

        return [
            TableElement(
                id=f"s{slide_idx}_sh{shape.shape_id}_tbl",
                bbox=bbox,
                data=data,
                headers=headers,
                hash=table_hash,
            )
        ]

    async def _parse_chart(
        self, shape: GraphicFrame, slide_idx: int, bbox: BoundingBox
    ) -> list[TableElement]:
        chart = shape.chart
        data = []
        headers = ["Series"]

        series_list = list(chart.series)
        if series_list:
            first_series = series_list[0]
            category_names = [cat.name for cat in first_series.categories]
            headers.extend(category_names)

        for series in chart.series:
            row_data = [series.name]
            for point in series.points:
                row_data.append(point.value)
            data.append(row_data)

        chart_hash = hashlib.md5(
            str(headers + data).encode("utf-8")
        ).hexdigest()

        return [
            TableElement(
                id=f"s{slide_idx}_sh{shape.shape_id}_chart",
                bbox=bbox,
                data=data,
                headers=headers,
                hash=chart_hash,
                is_chart=True,
            )
        ]