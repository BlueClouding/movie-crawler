import enum
from sqlalchemy import Enum

class SupportedLanguage(str, enum.Enum):
    ENGLISH = "en"
    JAPANESE = "ja"
    CHINESE = "zh"
    
# 创建SQLAlchemy枚举类型
SupportedLanguageEnum = Enum(
    SupportedLanguage,
    name="supported_language",
    create_constraint=False,  # 不创建约束，因为数据库中已经有了
    native_enum=True
)

class CrawlerStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"