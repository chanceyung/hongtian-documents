import hashlib
import re
from pathlib import Path
from typing import Any

from app.models.unified_document import (
    UnifiedDocument,
    TextElement,
    ImageElement,
    TableElement,
)


class MdParser:
    _HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)
    _IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    _TABLE_PATTERN = re.compile(r"(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n)*)")

    def __init__(self):
        self._session_id = ""
        self._assets_dir: Path | None = None
        self._base_dir: Path | None = None

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        self._session_id = session_id
        self._assets_dir = path.parent / "assets" / session_id
        self._assets_dir.mkdir(parents=True, exist_ok=True)
        self._base_dir = path.parent

        content = path.read_text(encoding="utf-8")

        try:
            import markdown_it
            md = markdown_it.MarkdownIt("commonmark", {"html": True}).enable("table")
            tokens = md.parse(content)
            texts, tables = await self._parse_tokens(tokens)
        except ImportError:
            texts, tables = await self._parse_with_regex(content)

        images = await self._extract_images(content)

        return UnifiedDocument(
            source_file=str(path),
            source_format="md",
            parse_method="markdown-it-py",
            texts=texts,
            images=images,
            tables=tables,
            parse_warnings=[],
            metadata={
                "total_texts": len(texts),
                "total_images": len(images),
                "total_tables": len(tables),
                "session_id": session_id,
            },
        )

    async def _parse_tokens(
        self, tokens
    ) -> tuple[list[TextElement], list[TableElement]]:
        texts = []
        tables = []

        for token in tokens:
            if token.type == "heading_open":
                level = int(token.tag[1])
                inline_token = self._find_next_inline(tokens, tokens.index(token))
                if inline_token and inline_token.content:
                    fingerprint = hashlib.md5(inline_token.content.encode("utf-8")).hexdigest()
                    texts.append(
                        TextElement(
                            id=f"md_heading_{len(texts)}",
                            content=inline_token.content,
                            page=0,
                            level=level,
                            fingerprint=fingerprint,
                        )
                    )
            elif token.type == "paragraph_open":
                inline_token = self._find_next_inline(tokens, tokens.index(token))
                if inline_token and inline_token.content:
                    fingerprint = hashlib.md5(inline_token.content.encode("utf-8")).hexdigest()
                    texts.append(
                        TextElement(
                            id=f"md_paragraph_{len(texts)}",
                            content=inline_token.content,
                            page=0,
                            level=0,
                            fingerprint=fingerprint,
                        )
                    )

        return texts, tables

    def _find_next_inline(self, tokens, start_idx):
        for token in tokens[start_idx:]:
            if token.type == "inline":
                return token
            elif token.type == "heading_close":
                break
        return None

    async def _parse_with_regex(
        self, content: str
    ) -> tuple[list[TextElement], list[TableElement]]:
        texts = []
        tables = []

        for match in self._HEADING_PATTERN.finditer(content):
            level = len(match.group(1).split()[0])
            text = match.group(1).lstrip("#").strip()
            fingerprint = hashlib.md5(text.encode("utf-8")).hexdigest()

            texts.append(
                TextElement(
                    id=f"md_heading_{len(texts)}",
                    content=text,
                    page=0,
                    level=level,
                    fingerprint=fingerprint,
                )
            )

        for match in self._TABLE_PATTERN.finditer(content):
            table_text = match.group(0)
            headers, data = self._parse_markdown_table(table_text)

            if headers or data:
                table_hash = hashlib.md5(
                    str(headers + data).encode("utf-8")
                ).hexdigest()

                tables.append(
                    TableElement(
                        id=f"md_table_{len(tables)}",
                        page=0,
                        data=data,
                        headers=headers,
                        hash=table_hash,
                    )
                )

        return texts, tables

    def _parse_markdown_table(self, table_text: str) -> tuple[list[str], list[list[str]]]:
        lines = [line.strip() for line in table_text.strip().split("\n")]
        if len(lines) < 2:
            return [], []

        if not lines[1].startswith("|") or not lines[1].endswith("|"):
            return [], []

        separator = lines[1][1:-1].strip()
        if not all(c in "|-:" for c in separator):
            return [], []

        headers = self._parse_table_row(lines[0])
        data = [self._parse_table_row(line) for line in lines[2:]]

        return headers, data

    def _parse_table_row(self, row: str) -> list[str]:
        if row.startswith("|") and row.endswith("|"):
            cells = row[1:-1].split("|")
        else:
            cells = row.split("|")

        return [cell.strip() for cell in cells]

    async def _extract_images(self, content: str) -> list[ImageElement]:
        images = []

        for match in self._IMAGE_PATTERN.finditer(content):
            alt_text = match.group(1)
            img_path = match.group(2)

            if img_path.startswith(("http://", "https://")):
                UnifiedDocument.parse_warnings.append(
                    f"External image skipped: {img_path}"
                )
                continue

            full_path = self._base_dir / img_path
            if not full_path.exists():
                UnifiedDocument.parse_warnings.append(
                    f"Image file not found: {full_path}"
                )
                continue

            try:
                image_data = full_path.read_bytes()
                image_hash = hashlib.md5(image_data).hexdigest()

                filename = full_path.name
                target_path = self._assets_dir / filename
                target_path.write_bytes(image_data)

                images.append(
                    ImageElement(
                        id=f"md_image_{len(images)}",
                        local_path=str(target_path.relative_to(target_path.parent.parent.parent)),
                        page=0,
                        hash=image_hash,
                        alt_text=alt_text,
                    )
                )
            except Exception as e:
                UnifiedDocument.parse_warnings.append(
                    f"Failed to save image {img_path}: {e}"
                )

        return images