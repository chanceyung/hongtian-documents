"""SVG post-processing pipeline for PPT Master compatibility."""

import base64
import re
from io import BytesIO
from pathlib import Path

from PIL import Image
from bs4 import BeautifulSoup


class SvgFinalizer:
    """Finalize SVG for PPT Master compatibility."""

    SAFE_FONTS = [
        "Arial",
        "Helvetica",
        "Calibri",
        "Times New Roman",
        "Verdana",
        "Georgia",
        "Trebuchet MS",
        "Tahoma",
    ]

    def finalize(self, svg_content: str, assets_dir: Path) -> str:
        """Run finalization pipeline on SVG content.

        Args:
            svg_content: Raw SVG content string
            assets_dir: Directory containing external assets (images, fonts, etc.)

        Returns:
            Finalized SVG content string
        """
        soup = BeautifulSoup(svg_content, "xml")
        svg = soup.find("svg")

        if not svg:
            raise ValueError("Invalid SVG: no root <svg> element found")

        self.embed_icons(soup, assets_dir)
        self.crop_and_embed_images(soup, assets_dir)
        self.fix_aspect_ratios(soup)
        self.flatten_text(soup)
        self.remove_incompatible(soup)
        self.quality_check(soup)

        return str(svg)

    def embed_icons(self, soup: BeautifulSoup, assets_dir: Path) -> None:
        """Embed external icon files as base64."""
        for image in soup.find_all("image"):
            href = image.get("href", "") or image.get("{http://www.w3.org/1999/xlink}href", "")

            if not href or href.startswith("data:"):
                continue

            icon_path = assets_dir / href
            if not icon_path.exists():
                continue

            try:
                with open(icon_path, "rb") as f:
                    img_data = f.read()
                    base64_data = base64.b64encode(img_data).decode()

                ext = icon_path.suffix[1:].lower()
                data_uri = f"data:image/{ext};base64,{base64_data}"
                image["href"] = data_uri
            except Exception:
                continue

    def crop_and_embed_images(self, soup: BeautifulSoup, assets_dir: Path) -> None:
        """Crop images to their bounding boxes and embed as base64."""
        for image in soup.find_all("image"):
            href = image.get("href", "") or image.get("{http://www.w3.org/1999/xlink}href", "")

            if not href.startswith("data:") and not href.startswith(("http://", "https://")):
                img_path = assets_dir / href
                if img_path.exists():
                    self._process_image_file(image, img_path)
            elif href.startswith("data:"):
                self._process_base64_image(image, href)

    def _process_image_file(self, image: Any, img_path: Path) -> None:
        """Process external image file."""
        try:
            with Image.open(img_path) as img:
                img = img.convert("RGBA")

                x = float(image.get("x", 0))
                y = float(image.get("y", 0))
                width = float(image.get("width", img.width))
                height = float(image.get("height", img.height))

                if width < img.width or height < img.height:
                    crop_x = int((img.width - width) / 2)
                    crop_y = int((img.height - height) / 2)
                    img = img.crop((crop_x, crop_y, crop_x + width, crop_y + height))

                buffered = BytesIO()
                img.save(buffered, format="PNG", optimize=True)
                base64_data = base64.b64encode(buffered.getvalue()).decode()

                image["href"] = f"data:image/png;base64,{base64_data}"
        except Exception:
            pass

    def _process_base64_image(self, image: Any, data_uri: str) -> None:
        """Process base64-encoded image."""
        match = re.match(r"data:image/([a-zA-Z]+);base64,(.+)", data_uri)
        if not match:
            return

        img_format = match.group(1).upper()
        if img_format not in ("PNG", "JPEG", "JPG"):
            return

        try:
            img_data = base64.b64decode(match.group(2))
            with Image.open(BytesIO(img_data)) as img:
                img = img.convert("RGBA")

                width = float(image.get("width", img.width))
                height = float(image.get("height", img.height))

                if width < img.width or height < img.height:
                    crop_x = int((img.width - width) / 2)
                    crop_y = int((img.height - height) / 2)
                    img = img.crop((crop_x, crop_y, crop_x + width, crop_y + height))

                buffered = BytesIO()
                img.save(buffered, format="PNG", optimize=True)
                base64_data = base64.b64encode(buffered.getvalue()).decode()

                image["href"] = f"data:image/png;base64,{base64_data}"
        except Exception:
            pass

    def fix_aspect_ratios(self, soup: BeautifulSoup) -> None:
        """Ensure all images have preserveAspectRatio set correctly."""
        for image in soup.find_all("image"):
            if "preserveAspectRatio" not in image.attrs:
                image["preserveAspectRatio"] = "xMidYMid slice"

    def flatten_text(self, soup: BeautifulSoup) -> None:
        """Flatten text elements and ensure inline styles."""
        for text in soup.find_all("text"):
            for attr in list(text.attrs.keys()):
                if attr.startswith("class"):
                    del text[attr]

            font_family = text.get("font-family", "")
            if font_family:
                safe_font = next(
                    (f for f in self.SAFE_FONTS if f.lower() in font_family.lower()),
                    "Arial",
                )
                text["font-family"] = safe_font
            else:
                text["font-family"] = "Arial"

            for tspan in text.find_all("tspan"):
                tspan["font-family"] = text["font-family"]
                if "x" not in tspan.attrs:
                    tspan["x"] = text.get("x", 0)
                if "y" not in tspan.attrs:
                    tspan["y"] = text.get("y", 0)

    def remove_incompatible(self, soup: BeautifulSoup) -> None:
        """Remove elements incompatible with PPT Master."""
        for mask in soup.find_all("mask"):
            mask.decompose()

        for pattern in soup.find_all("pattern"):
            pattern.decompose()

        for filter_elem in soup.find_all("filter"):
            filter_elem.decompose()

        for elem in soup.find_all(recursive=True):
            for attr in list(elem.attrs.keys()):
                if attr == "class":
                    del elem[attr]

        style_tag = soup.find("style")
        if style_tag:
            content = style_tag.string or ""
            content = re.sub(r"@font-face\s*{[^}]*}", "", content, flags=re.DOTALL)
            content = re.sub(r"\.[a-zA-Z_-]+\s*{[^}]*}", "", content, flags=re.DOTALL)
            style_tag.string = content

        svg = soup.find("svg")
        if svg and "style" in svg.attrs:
            del svg["style"]

    def quality_check(self, soup: BeautifulSoup) -> None:
        """Perform quality checks and raise errors if issues found."""
        svg = soup.find("svg")

        if not svg.get("viewBox") and not svg.get("viewbox"):
            raise ValueError("Quality check failed: SVG missing viewBox attribute")

        if svg.find("mask"):
            raise ValueError("Quality check failed: SVG still contains mask elements")

        if svg.find("filter"):
            raise ValueError("Quality check failed: SVG still contains filter elements")

        style_tag = svg.find("style")
        if style_tag:
            content = style_tag.string or ""
            if "@font-face" in content:
                raise ValueError("Quality check failed: SVG still contains @font-face")

        for elem in svg.find_all(class_=True):
            raise ValueError("Quality check failed: SVG still contains class attributes")

        for image in svg.find_all("image"):
            href = image.get("href", "") or image.get("{http://www.w3.org/1999/xlink}href", "")
            if not href:
                raise ValueError("Quality check failed: Image missing href attribute")
            if not href.startswith("data:"):
                raise ValueError("Quality check failed: Image not embedded as base64")