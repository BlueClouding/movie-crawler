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
    create_constraint=False,
    native_enum=True,
    values_callable=lambda enum: [member.value for member in enum]  # 关键点！
)

class CrawlerStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"
    NEW = "new"

class CrawlerTaskType(str, enum.Enum):
    GENRES = "genres"
    GENRES_PAGES = "genres_pages"
    MOVIES = "movies"
    ACTRESSES = "actresses"