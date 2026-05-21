import hashlib
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.drawing.image import Image

from app.models.unified_document import (
    UnifiedDocument,
    TextElement,
    ImageElement,
    TableElement,
    BoundingBox,
)


class XlsxParser:
    def __init__(self):
        self._session_id = ""
        self._assets_dir: Path | None = None

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        self._session_id = session_id
        self._assets_dir = path.parent / "assets" / session_id
        self._assets_dir.mkdir(parents=True, exist_ok=True)

        workbook = openpyxl.load_workbook(str(path), data_only=True)

        texts = []
        images = []
        tables = []
        warnings = []

        for sheet_name, sheet in workbook.worksheets:
            try:
                sheet_texts, sheet_tables, sheet_images = await self._parse_sheet(
                    sheet, sheet_name, path
                )
                texts.extend(sheet_texts)
                tables.extend(sheet_tables)
                images.extend(sheet_images)
            except Exception as e:
                warnings.append(f"Sheet '{sheet_name}' parse error: {e}")

        workbook.close()

        return UnifiedDocument(
            source_file=str(path),
            source_format="xlsx",
            parse_method="openpyxl",
            texts=texts,
            images=images,
            tables=tables,
            parse_warnings=warnings,
            metadata={
                "total_sheets": len(workbook.worksheets),
                "total_texts": len(texts),
                "total_tables": len(tables),
                "total_images": len(images),
                "session_id": session_id,
            },
        )

    async def _parse_sheet(
        self, sheet, sheet_name: str, file_path: Path
    ) -> tuple[list[TextElement], list[TableElement], list[ImageElement]]:
        texts = []
        tables = []
        images = []

        data = []
        for row in sheet.iter_rows(values_only=True):
            row_data = [str(cell) if cell is not None else "" for cell in row]
            data.append(row_data)

        filtered_data = self._filter_empty_rows_and_columns(data)

        if filtered_data:
            headers = filtered_data[0]
            table_data = filtered_data[1:] if len(filtered_data) > 1 else []

            table_hash = hashlib.md5(
                str(headers + table_data).encode("utf-8")
            ).hexdigest()

            table_id = f"xlsx_{sheet_name}"
            tables.append(
                TableElement(
                    id=table_id,
                    page=0,
                    data=table_data,
                    headers=headers,
                    hash=table_hash,
                )
            )

            for idx, header in enumerate(headers):
                if header.strip():
                    fingerprint = hashlib.md5(header.encode("utf-8")).hexdigest()
                    texts.append(
                        TextElement(
                            id=f"{table_id}_h{idx}",
                            content=header,
                            page=0,
                            level=1,
                            fingerprint=fingerprint,
                        )
                    )

        if hasattr(sheet, "_images"):
            for img_idx, img in enumerate(sheet._images):
                try:
                    image_path = await self._save_image(img, sheet_name, img_idx)
                    image_hash = hashlib.md5(image_path.read_bytes()).hexdigest()

                    images.append(
                        ImageElement(
                            id=f"xlsx_{sheet_name}_img{img_idx}",
                            local_path=str(image_path.relative_to(image_path.parent.parent.parent)),
                            page=0,
                            hash=image_hash,
                            width=img.width,
                            height=img.height,
                        )
                    )
                except Exception as e:
                    UnifiedDocument.parse_warnings.append(
                        f"Image {img_idx} in sheet '{sheet_name}' save error: {e}"
                    )

        return texts, tables, images

    def _filter_empty_rows_and_columns(self, data: list[list[str]]) -> list[list[str]]:
        if not data:
            return []

        non_empty_rows = [row for row in data if any(cell.strip() for cell in row)]

        if not non_empty_rows:
            return []

        max_cols = max(len(row) for row in non_empty_rows)
        non_empty_cols = []

        for col_idx in range(max_cols):
            has_content = any(
                len(row) > col_idx and row[col_idx].strip()
                for row in non_empty_rows
            )
            if has_content:
                non_empty_cols.append(col_idx)

        filtered_data = [
            [row[col_idx] if col_idx < len(row) else "" for col_idx in non_empty_cols]
            for row in non_empty_rows
        ]

        return filtered_data

    async def _save_image(self, img: Image, sheet_name: str, img_idx: int) -> Path:
        ext = img.format.lower() if img.format else "png"
        filename = f"xlsx_{sheet_name}_img{img_idx}.{ext}"
        image_path = self._assets_dir / filename

        img.save(str(image_path))

        return image_path