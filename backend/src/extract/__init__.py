"""文档文本提取与上传格式校验（基础设施层，注册表驱动）。

加一种新格式 = 在 ``extract.registry.FORMAT_REGISTRY`` 注册一项（含魔数与
解析器 kind）；需要新解析器时在 ``extract.extractors`` 增加对应函数。路由层
只做 HTTP 适配，不承载格式/解析逻辑。
"""

from .extractors import extract_text
from .registry import ALLOWED_CONTENT_TYPES, MAX_FILE_SIZE_MB, validate_magic, validate_upload

__all__ = [
    "ALLOWED_CONTENT_TYPES",
    "MAX_FILE_SIZE_MB",
    "extract_text",
    "validate_magic",
    "validate_upload",
]
