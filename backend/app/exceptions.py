"""自定义异常层级"""


class MagazineError(Exception):
    """基础异常"""
    def __init__(self, message: str, code: str = "MAGAZINE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ParseError(MagazineError):
    """文档解析异常"""
    def __init__(self, message: str, format: str = ""):
        self.format = format
        super().__init__(message, code="PARSE_ERROR")


class FidelityError(MagazineError):
    """保真校验异常"""
    def __init__(self, message: str, score: float = 0.0):
        self.score = score
        super().__init__(message, code="FIDELITY_ERROR")


class RenderError(MagazineError):
    """渲染异常"""
    def __init__(self, message: str, engine: str = ""):
        self.engine = engine
        super().__init__(message, code="RENDER_ERROR")


class SupplementError(MagazineError):
    """素材补充异常"""
    def __init__(self, message: str, provider: str = ""):
        self.provider = provider
        super().__init__(message, code="SUPPLEMENT_ERROR")


class WorkflowError(MagazineError):
    """工作流异常"""
    def __init__(self, message: str, stage: str = ""):
        self.stage = stage
        super().__init__(message, code="WORKFLOW_ERROR")
