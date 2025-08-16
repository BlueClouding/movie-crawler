import logging
from typing import Dict, List, Optional, Any
from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from common.db.entity.download_url import DownloadUrl

class DownloadUrlRepository:
    """下载链接仓库类，处理磁力链接和下载URL的数据库操作"""
    
    def __init__(self, db: AsyncSession):
        """
        初始化下载链接仓库
        
        Args:
            db: 异步数据库会话
        """
        self.db = db
        self._logger = logging.getLogger(__name__)
    
    async def create_download_url(self, download_url_data: Dict[str, Any]) -> Optional[DownloadUrl]:
        """
        创建新的下载链接记录
        
        Args:
            download_url_data: 下载链接数据
            
        Returns:
            创建的下载链接记录，如果失败则为None
        """
        try:
            download_url = DownloadUrl(**download_url_data)
            self.db.add(download_url)
            await self.db.commit()
            await self.db.refresh(download_url)
            return download_url
        except Exception as e:
            self._logger.error(f"Error creating download url: {str(e)}")
            await self.db.rollback()
            return None
    
    async def get_download_url_by_code(self, code: str) -> Optional[DownloadUrl]:
        """
        根据从link字段提取的电影代码获取下载链接
        
        Args:
            code: 从link字段提取的电影代码，如从'v/snis-264-uncensored-leaked'提取'snis-264-uncensored-leaked'
            
        Returns:
            下载链接记录，如果不存在则为None
        """
        try:
            query = select(DownloadUrl).where(DownloadUrl.code == code)
            result = await self.db.execute(query)
            return result.scalars().first()
        except Exception as e:
            self._logger.error(f"Error getting download url for code {code}: {str(e)}")
            return None
    
    async def update_download_url(self, code: str, magnets: str) -> Optional[DownloadUrl]:
        """
        更新下载链接
        
        Args:
            code: 从link字段提取的电影代码，如从'v/snis-264-uncensored-leaked'提取'snis-264-uncensored-leaked'
            magnets: 磁力链接
            
        Returns:
            更新后的下载链接记录，如果失败则为None
        """
        try:
            download_url = await self.get_download_url_by_code(code)
            
            if download_url:
                download_url.magnets = magnets
                await self.db.commit()
                await self.db.refresh(download_url)
                return download_url
            else:
                # 如果不存在，创建新记录
                return await self.create_download_url({
                    'code': code,
                    'magnets': magnets
                })
        except Exception as e:
            self._logger.error(f"Error updating download url for code {code}: {str(e)}")
            await self.db.rollback()
            return None
    
    async def delete_download_url(self, code: str) -> bool:
        """
        删除下载链接
        
        Args:
            code: 从link字段提取的电影代码，如从'v/snis-264-uncensored-leaked'提取'snis-264-uncensored-leaked'
            
        Returns:
            是否成功删除
        """
        try:
            query = select(DownloadUrl).where(DownloadUrl.code == code)
            result = await self.db.execute(query)
            download_url = result.scalars().first()
            
            if download_url:
                await self.db.delete(download_url)
                await self.db.commit()
                return True
            return False
        except Exception as e:
            self._logger.error(f"Error deleting download url for code {code}: {str(e)}")
            await self.db.rollback()
            return False
