"""V4 架构配置管理"""
import warnings
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Magazine Document Agent"
    DEBUG: bool = False
    PORT: int = 8000

    # 数据库
    DATABASE_URL: str = "sqlite:///./app_data/magazine.db"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # 文件存储
    UPLOAD_DIR: str = "./data/uploads"
    OUTPUT_DIR: str = "./data/output"
    ASSETS_DIR: str = "./data/assets"
    TEMPLATE_DIR: str = "./app/templates"

    # 安全
    API_KEY_ENCRYPTION_KEY: str = "change-me-in-production-32byte"
    MAX_UPLOAD_SIZE_MB: int = 100
    CORS_ORIGINS: list = ['http://localhost:3000', 'http://localhost:8000']

    # GLM-5 API
    LLM: str = "custom"
    CUSTOM_LLM_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    CUSTOM_MODEL: str = "glm-4-flash"
    CUSTOM_LLM_API_KEY: str = ""

    # 素材补充
    IMAGE_PROVIDER: str = "pexels"
    PEXELS_API_KEY: str = ""
    UNSPLASH_ACCESS_KEY: str = ""
    REPLICATE_API_TOKEN: str = ""

    # 保真校验
    FIDELITY_THRESHOLD: float = 0.95
    MAX_REPAIR_ATTEMPTS: int = 2

    # Docling
    DOCILING_TIMEOUT: int = 300

    # Playwright
    PLAYWRIGHT_HEADLESS: bool = True

    # 模板
    MAGAZINE_TEMPLATES_DIR: str = "./app/templates"

    @field_validator("API_KEY_ENCRYPTION_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if v == "change-me-in-production-32byte":
            warnings.warn(
                "使用默认加密密钥，请在生产环境中更换 API_KEY_ENCRYPTION_KEY",
                stacklevel=2
            )
        if len(v.encode()) < 16:
            raise ValueError("API_KEY_ENCRYPTION_KEY 长度至少 16 字节")
        return v

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
