"""设计规范模型 — PPT Master 风格的设计规范"""
from pydantic import BaseModel


class ColorScheme(BaseModel):
    primary: str = "#2E86AB"
    secondary: str = "#F24236"
    accent: str = "#A23B72"
    background: str = "#FAFAFA"
    text: str = "#333333"
    muted: str = "#888888"


class Typography(BaseModel):
    title_font: str = "Arial"
    body_font: str = "Arial"
    title_size: int = 48
    subtitle_size: int = 32
    body_size: int = 24
    caption_size: int = 18


class DesignSpec(BaseModel):
    canvas_format: str = "ppt169"
    canvas_width: int = 1920
    canvas_height: int = 1080
    colors: ColorScheme
    typography: Typography = Typography()
    icon_library: str = "tabler-filled"
    target_pages: int = 10
    style: str = "modern_professional"
