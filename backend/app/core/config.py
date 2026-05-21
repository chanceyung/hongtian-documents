"""V4 架构配置管理"""
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

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


settings = Settings()
