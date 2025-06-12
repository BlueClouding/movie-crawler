from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from common.db.entity.base import DBBaseModel


class DownloadUrl(DBBaseModel):
    """下载链接表"""

    __tablename__ = "download_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    magnets = Column(Text, nullable=False, comment="磁力链接")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), comment="创建时间"
    )
    code = Column(String(233), nullable=True, comment="电影代码")

    def __repr__(self):
        return f"<DownloadUrl(id={self.id}, code={self.code})>"
