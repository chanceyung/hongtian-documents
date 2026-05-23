"""混合 PDF 渲染引擎 — 视觉页用 Playwright，文字/表格页用 WeasyPrint"""
import io
from pathlib import Path

from app.models.edit_actions import MagazineEditPlan
from app.models.unified_document import UnifiedDocument


class HybridPdfRenderer:

    PLAYWRIGHT_TYPES = {"cover", "hero", "data_card", "full_image", "quote"}
    WEASYPRINT_TYPES = {"text_only", "text_table", "text_image", "two_column"}

    async def render(
        self,
        plan: MagazineEditPlan,
        doc: UnifiedDocument,
        template_dir: Path,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        pdf_pages: list[bytes] = []

        template_root = template_dir / plan.template_id
        template_html_path = template_root / "template.html"
        css_path = template_root / "styles.css"

        template_html = template_html_path.read_text("utf-8") if template_html_path.exists() else "<html><body>{{content}}</body></html>"
        css_content = css_path.read_text("utf-8") if css_path.exists() else ""

        filled_pages = self._fill_template(template_html, css_content, plan, doc)

        for page_info in filled_pages:
            layout_type = page_info["layout_type"]
            page_html = page_info["html"]

            if layout_type in self.PLAYWRIGHT_TYPES:
                pdf_bytes = await self._render_playwright(page_html, css_content)
            else:
                pdf_bytes = await self._render_weasyprint(page_html, css_content)

            pdf_pages.append(pdf_bytes)

        if pdf_pages:
            self._merge_pdfs(pdf_pages, output_path)
        else:
            self._create_empty_pdf(output_path)

        return output_path

    def _fill_template(
        self,
        template_html: str,
        css_content: str,
        plan: MagazineEditPlan,
        doc: UnifiedDocument,
    ) -> list[dict]:
        from bs4 import BeautifulSoup

        pages: list[dict] = []

        for page_plan in plan.pages:
            soup = BeautifulSoup(template_html, "html.parser")

            style_tag = soup.find("style")
            if style_tag:
                style_tag.string = css_content
            else:
                head = soup.find("head")
                if head:
                    style_tag = soup.new_tag("style")
                    style_tag.string = css_content
                    head.append(style_tag)

            page_container = soup.select_one(
                f'[data-page-type="{page_plan.template_page}"]',
            )
            if not page_container:
                page_container = soup.find("body")

            if page_container:
                for action in page_plan.actions:
                    target = soup.select_one(action.target_selector)
                    if not target:
                        continue

                    if action.type == "replace_text":
                        target.string = action.content or ""
                    elif action.type == "replace_image":
                        img = doc.find_image(action.source_id)
                        if img:
                            target["src"] = img.local_path
                            target["style"] = "max-width: 100%; height: auto;"
                    elif action.type == "replace_table_data":
                        tbl = doc.find_table(action.source_id)
                        if tbl:
                            table_html = self._build_table_html(tbl.data, tbl.headers)
                            target.replace_with(BeautifulSoup(table_html, "html.parser"))

            pages.append({
                "layout_type": page_plan.template_page,
                "html": str(soup),
            })

        return pages

    def _build_table_html(self, data: list[list[str]], headers: list[str]) -> str:
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

    async def _render_playwright(self, html: str, css: str) -> bytes:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(html, wait_until="networkidle")
            await page.add_style_tag(content=f"{css}\n@page {{ size: A4; margin: 0; }}\nbody {{ margin: 0; }}")
            pdf_bytes = await page.pdf(format="A4", print_background=True, prefer_css_page_size=True)
            await browser.close()
            return pdf_bytes

    async def _render_weasyprint(self, html: str, css: str) -> bytes:
        try:
            from weasyprint import HTML, CSS

            table_css = css + """
            table { page-break-inside: auto; }
            tr    { page-break-inside: avoid; page-break-after: auto; }
            td    { page-break-inside: avoid; }
            thead { display: table-header-group; }
            tfoot { display: table-footer-group; }
            """
            html_doc = HTML(string=html)
            css_doc = CSS(string=table_css)
            return html_doc.write_pdf(stylesheets=[css_doc])
        except (ImportError, OSError):
            return await self._render_playwright(html, css)

    def _merge_pdfs(self, pdf_pages: list[bytes], output_path: Path) -> None:
        from PyPDF2 import PdfMerger

        merger = PdfMerger()
        for pdf_bytes in pdf_pages:
            merger.append(io.BytesIO(pdf_bytes))
        merger.write(str(output_path))
        merger.close()

    def _create_empty_pdf(self, output_path: Path) -> None:
        from PyPDF2 import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=595, height=842)
        writer.write(str(output_path))
        writer.close()


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
