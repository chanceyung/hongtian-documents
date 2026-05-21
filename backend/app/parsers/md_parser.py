"""Markdown 解析 — markdown-it-py + regex 降级"""
import hashlib
import re
from pathlib import Path

from app.models.unified_document import (
    UnifiedDocument,
    TextElement,
    ImageElement,
    TableElement,
)


class MdParser:
    _HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
    _IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    _TABLE_PATTERN = re.compile(r"(\|.+\|\n\|[-:| ]+\|\n(?:\|.+\|\n)*)")

    async def parse(self, path: Path, session_id: str) -> UnifiedDocument:
        assets_dir = path.parent / "assets" / session_id
        assets_dir.mkdir(parents=True, exist_ok=True)
        base_dir = path.parent
        warnings: list[str] = []

        content = path.read_text(encoding="utf-8")

        try:
            import markdown_it
            md = markdown_it.MarkdownIt("commonmark", {"html": True}).enable("table")
            tokens = md.parse(content)
            texts, tables = self._parse_tokens(tokens)
        except ImportError:
            texts, tables = self._parse_with_regex(content)

        images = self._extract_images(content, base_dir, assets_dir, warnings)

        return UnifiedDocument(
            source_file=str(path),
            source_format="md",
            parse_method="markdown-it-py",
            texts=texts,
            images=images,
            tables=tables,
            parse_warnings=warnings,
        )

    def _parse_tokens(self, tokens) -> tuple[list[TextElement], list[TableElement]]:
        texts: list[TextElement] = []
        tables: list[TableElement] = []
        i = 0

        while i < len(tokens):
            token = tokens[i]
            if token.type == "heading_open":
                level = int(token.tag[1])
                i += 1
                if i < len(tokens) and tokens[i].type == "inline":
                    text = tokens[i].content.strip()
                    if text:
                        texts.append(TextElement(
                            id=f"md_heading_{len(texts)}",
                            content=text,
                            page=0,
                            level=level,
                            fingerprint=hashlib.md5(text.encode()).hexdigest(),
                        ))
            elif token.type == "paragraph_open":
                i += 1
                if i < len(tokens) and tokens[i].type == "inline":
                    text = tokens[i].content.strip()
                    if text:
                        texts.append(TextElement(
                            id=f"md_para_{len(texts)}",
                            content=text,
                            page=0,
                            level=0,
                            fingerprint=hashlib.md5(text.encode()).hexdigest(),
                        ))
            elif token.type == "table_open":
                headers, data, i = self._parse_flat_table(tokens, i)
                if headers or data:
                    tables.append(TableElement(
                        id=f"md_table_{len(tables)}",
                        page=0,
                        data=data,
                        headers=headers,
                    ))
                continue
            i += 1

        return texts, tables

    def _parse_flat_table(
        self, tokens: list, start: int,
    ) -> tuple[list[str], list[list[str]], int]:
        headers: list[str] = []
        rows: list[list[str]] = []
        current_row: list[str] = []
        in_header = False
        i = start + 1

        while i < len(tokens):
            t = tokens[i]
            if t.type == "table_close":
                i += 1
                break
            elif t.type == "thead_open":
                in_header = True
            elif t.type == "thead_close":
                in_header = False
            elif t.type == "tr_open":
                current_row = []
            elif t.type == "tr_close":
                if in_header:
                    headers = current_row
                else:
                    rows.append(current_row)
                current_row = []
            elif t.type == "inline":
                current_row.append(t.content.strip())
            i += 1

        return headers, rows, i

    def _parse_with_regex(self, content: str) -> tuple[list[TextElement], list[TableElement]]:
        texts: list[TextElement] = []
        tables: list[TableElement] = []

        for match in self._HEADING_PATTERN.finditer(content):
            level = len(match.group(1))
            text = match.group(2).strip()
            texts.append(TextElement(
                id=f"md_heading_{len(texts)}",
                content=text,
                page=0,
                level=level,
                fingerprint=hashlib.md5(text.encode()).hexdigest(),
            ))

        for match in self._TABLE_PATTERN.finditer(content):
            table_text = match.group(0)
            headers, data = self._parse_markdown_table(table_text)
            if headers or data:
                tables.append(TableElement(
                    id=f"md_table_{len(tables)}",
                    page=0,
                    data=data,
                    headers=headers,
                ))

        return texts, tables

    def _parse_markdown_table(self, table_text: str) -> tuple[list[str], list[list[str]]]:
        lines = [line.strip() for line in table_text.strip().split("\n")]
        if len(lines) < 2:
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

    def _extract_images(
        self, content: str, base_dir: Path, assets_dir: Path, warnings: list[str],
    ) -> list[ImageElement]:
        images: list[ImageElement] = []

        for match in self._IMAGE_PATTERN.finditer(content):
            alt_text = match.group(1)
            img_ref = match.group(2)

            if img_ref.startswith(("http://", "https://")):
                warnings.append(f"External image skipped: {img_ref}")
                continue

            full_path = base_dir / img_ref
            if not full_path.exists():
                warnings.append(f"Image not found: {full_path}")
                continue

            try:
                img_bytes = full_path.read_bytes()
                img_hash = hashlib.md5(img_bytes).hexdigest()[:12]
                target = assets_dir / full_path.name
                target.write_bytes(img_bytes)

                images.append(ImageElement(
                    id=f"md_img_{len(images)}",
                    local_path=str(target),
                    page=0,
                    hash=img_hash,
                    alt_text=alt_text,
                ))
            except Exception as e:
                warnings.append(f"Image copy failed: {e}")

        return images
