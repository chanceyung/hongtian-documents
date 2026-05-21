"""Renderer Agent — 双轨渲染：PDF路径 + PPTX路径"""
import base64
from pathlib import Path

from app.models.edit_actions import MagazineEditPlan
from app.models.unified_document import UnifiedDocument


class RendererAgent:
    """根据输出格式选择渲染引擎"""

    async def render_pptx(
        self, plan: MagazineEditPlan, doc: UnifiedDocument, template_dir: Path, output_path: Path,
    ) -> Path:
        from app.exporters.ppt_master.svg_to_pptx import SvgToPptxConverter
        from app.exporters.ppt_master.finalize_svg import SvgFinalizer

        template_root = template_dir / plan.template_id
        svg_pages: list[str] = []

        for page in plan.pages:
            svg_template = self._load_svg_template(template_root, page.template_page)
            if svg_template:
                svg_filled = self._apply_edit_actions_svg(svg_template, page, doc)
                svg_pages.append(svg_filled)

        if not svg_pages:
            svg_pages.append(self._create_fallback_svg(plan, doc))

        assets_dir = Path(doc.source_file).parent / "assets"
        finalizer = SvgFinalizer()
        finalized_svgs = [finalizer.finalize(svg, assets_dir) for svg in svg_pages]

        template_pptx = template_root / "template.pptx"
        converter = SvgToPptxConverter()
        converter.convert(
            finalized_svgs,
            plan.design_spec,
            output_path,
            template_pptx if template_pptx.exists() else None,
        )

        return output_path

    async def render_pdf(
        self, plan: MagazineEditPlan, doc: UnifiedDocument, template_dir: Path, output_path: Path,
    ) -> Path:
        from app.exporters.pdf_renderer import HybridPdfRenderer

        renderer = HybridPdfRenderer()
        return await renderer.render(plan, doc, template_dir, output_path)

    def _load_svg_template(self, template_root: Path, layout_type: str) -> str | None:
        layout_to_file = {
            "cover": "cover.svg",
            "text_only": "content_text.svg",
            "text_image": "content_image_text.svg",
            "data_card": "data_card.svg",
        }
        filename = layout_to_file.get(layout_type, "content_text.svg")
        svg_path = template_root / "pages" / filename
        if svg_path.exists():
            return svg_path.read_text(encoding="utf-8")
        return None

    def _apply_edit_actions_svg(self, svg_template: str, page, doc: UnifiedDocument) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(svg_template, "xml")

        for action in page.actions:
            target = soup.select_one(action.target_selector)
            if not target:
                continue

            if action.type == "replace_text":
                target.string = action.content or ""

            elif action.type == "replace_image":
                img = doc.find_image(action.source_id)
                if img:
                    img_path = Path(img.local_path)
                    if img_path.exists():
                        img_b64 = base64.b64encode(img_path.read_bytes()).decode()
                        ext = img_path.suffix.lstrip(".")
                        mime = {"jpg": "jpeg", "png": "png", "gif": "gif"}.get(ext, "jpeg")
                        target["href"] = f"data:image/{mime};base64,{img_b64}"

        return str(soup)

    def _create_fallback_svg(self, plan: MagazineEditPlan, doc: UnifiedDocument) -> str:
        texts = []
        for page in plan.pages:
            for action in page.actions:
                if action.type == "replace_text" and action.content:
                    texts.append(f'<text x="100" y="{120 + len(texts) * 40}" '
                                 f'font-family="Arial" font-size="20" fill="#333333">'
                                 f'{action.content[:100]}</text>')

        return f'''<svg viewBox="0 0 1920 1080" width="1920" height="1080"
                    xmlns="http://www.w3.org/2000/svg">
                   <rect width="1920" height="1080" fill="#ffffff"/>
                   {"".join(texts)}
                 </svg>'''
