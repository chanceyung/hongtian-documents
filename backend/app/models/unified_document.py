"""统一文档模型 — 所有解析器输出此格式，所有下游模块消费此格式"""
import hashlib

from pydantic import BaseModel
from typing import Literal


class BoundingBox(BaseModel):
    """统一坐标格式（EMU单位，与PPTX一致）"""
    left: int
    top: int
    width: int
    height: int


class TextElement(BaseModel):
    id: str
    content: str
    page: int
    bbox: BoundingBox | None = None
    level: int = 0  # 0=正文, 1=一级标题, 2=二级...
    style: str = "Normal"
    fingerprint: str = ""


class ImageElement(BaseModel):
    id: str
    local_path: str
    page: int
    bbox: BoundingBox | None = None
    width: int = 0
    height: int = 0
    hash: str = ""
    alt_text: str = ""


class TableElement(BaseModel):
    id: str
    page: int
    bbox: BoundingBox | None = None
    data: list[list[str]]
    headers: list[str] = []
    is_chart: bool = False


class ContentAssetLink(BaseModel):
    """图片-文字关联关系"""
    text_id: str
    asset_id: str
    asset_type: Literal["image", "table"]
    strategy: str  # spatial | structural | semantic
    confidence: float


class ContentFingerprint(BaseModel):
    """内容指纹 — 用于保真校验"""
    text_fingerprints: dict[str, str]
    image_hashes: dict[str, str]
    text_count: int
    image_count: int
    table_count: int
    total_chars: int


class UnifiedDocument(BaseModel):
    """统一文档模型 — 所有模块的数据交换格式"""
    source_file: str
    source_format: str  # pptx | pdf | docx | xlsx | md
    title: str = ""

    texts: list[TextElement] = []
    images: list[ImageElement] = []
    tables: list[TableElement] = []
    linkage: list[ContentAssetLink] = []

    total_pages: int = 0
    parse_method: str = ""
    parse_warnings: list[str] = []

    def compute_fingerprint(self) -> ContentFingerprint:
        return ContentFingerprint(
            text_fingerprints={
                t.id: hashlib.md5(t.content.encode()).hexdigest()
                for t in self.texts
            },
            image_hashes={img.id: img.hash for img in self.images},
            text_count=len(self.texts),
            image_count=len(self.images),
            table_count=len(self.tables),
            total_chars=sum(len(t.content) for t in self.texts),
        )

    def find_image(self, image_id: str) -> ImageElement | None:
        return next((i for i in self.images if i.id == image_id), None)

    def find_table(self, table_id: str) -> TableElement | None:
        return next((t for t in self.tables if t.id == table_id), None)
