"""编辑动作模型 — PPTAgent 风格：只替换，不重写"""
from pydantic import BaseModel
from typing import Literal


class EditAction(BaseModel):
    type: Literal["replace_text", "replace_image", "replace_table_data"]
    target_selector: str
    source_id: str
    content: str | None = None
    confidence: float = 1.0


class SlideEditPlan(BaseModel):
    page_number: int
    template_page: str
    actions: list[EditAction] = []
    notes: str = ""


class MagazineEditPlan(BaseModel):
    document_id: str
    template_id: str
    pages: list[SlideEditPlan] = []
    design_spec: dict = {}
    original_fingerprint: dict = {}
