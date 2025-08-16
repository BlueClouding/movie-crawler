"""数据库管理工具类，提供数据库连接和基本操作功能"""

import logging
import os
from typing import List, Optional, Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

logger = logging.getLogger(__name__)

class DatabaseManager:
    """数据库管理工具类
    
    提供数据库连接、会话管理和基本操作功能
    """
    
    def __init__(self):
        """初始化数据库管理器"""
        # 从环境变量获取数据库 URL，如果没有则使用默认值
        database_url = os.getenv(
            'DATABASE_URL', 
            'postgresql+asyncpg://postgres:123456@localhost:5432/movie_crawler'
        )
        
        # 创建异步引擎
        self.engine = create_async_engine(
            database_url,
            echo=True,  # 输出 SQL 日志
            future=True  # 启用 SQLAlchemy 2.0 特性
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取数据库会话的上下文管理器
        
        Yields:
            AsyncSession: 数据库会话
        """
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"数据库操作失败: {e}")
                raise
            finally:
                await session.close()
    
    async def execute_migration(self, migration_file_path: str) -> bool:
        """执行SQL迁移文件
        
        Args:
            migration_file_path: 迁移文件路径
            
        Returns:
            bool: 执行是否成功
        """
        try:
            with open(migration_file_path, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            async with self.get_session() as session:
                # 分割SQL语句并执行
                statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                for statement in statements:
                    if statement:
                        await session.execute(text(statement))
                        
            logger.info(f"成功执行迁移文件: {migration_file_path}")
            return True
            
        except Exception as e:
            logger.error(f"执行迁移文件失败 {migration_file_path}: {e}")
            return False
    
    async def get_pending_movie_codes(self, limit: int = 10) -> List[str]:
        """获取待爬取的电影URL
        
        Args:
            limit: 获取数量限制
            
        Returns:
            List[str]: MissAV完整URL列表
        """
        try:
            async with self.get_session() as session:
                # 查询 miss_status 为 NULL 或 'pending' 的电影，返回完整的link字段
                query = text("""
                    SELECT link FROM movies 
                    WHERE miss_status IS NULL OR miss_status = 'pending'
                    AND link IS NOT NULL
                    ORDER BY created_at ASC
                    LIMIT :limit
                """)
                
                result = await session.execute(query, {"limit": limit})
                links = [row[0] for row in result.fetchall()]
                
                # 将link字段转换为完整的MissAV URL
                movie_urls = []
                for link in links:
                    if link:
                        # 从'dm3/v/345simm-656'提取'345simm-656'，然后构建完整URL
                        movie_code = link.split('/')[-1]
                        movie_url = f"https://missav.ai/ja/{movie_code}"
                        movie_urls.append(movie_url)
                    else:
                        logger.warning(f"无效的link格式: {link}")
                
                logger.info(f"获取到 {len(movie_urls)} 个待爬取的电影URL")
                return movie_urls
                
        except Exception as e:
            logger.error(f"获取待爬取电影URL失败: {e}")
            return []
    
    async def update_movie_status(self, movie_urls: List[str], status: str) -> bool:
        """更新电影状态
        
        Args:
            movie_urls: 电影URL列表
            status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        try:
            async with self.get_session() as session:
                for movie_url in movie_urls:
                    # 从URL中提取电影代码，例如从'https://missav.ai/ja/jur-319'提取'jur-319'
                    movie_code = movie_url.split('/')[-1]
                    # 根据电影代码更新状态，使用LIKE匹配link字段中包含该代码的记录
                    await session.execute(
                        text("UPDATE movies SET miss_status = :status WHERE link LIKE :pattern"),
                        {"status": status, "pattern": f"%/{movie_code}"}
                    )
                await session.commit()
                logger.info(f"成功更新 {len(movie_urls)} 个电影状态为 {status}")
                return True
        except Exception as e:
            logger.error(f"更新电影状态失败: {e}")
            return False
    
    async def get_movie_status_count(self) -> Dict[str, int]:
        """获取各状态电影的数量统计
        
        Returns:
            Dict[str, int]: 状态统计字典
        """
        try:
            async with self.get_session() as session:
                query = text("""
                    SELECT 
                        COALESCE(miss_status, 'pending') as status,
                        COUNT(*) as count
                    FROM movies 
                    GROUP BY COALESCE(miss_status, 'pending')
                    ORDER BY status
                """)
                
                result = await session.execute(query)
                status_count = {row[0]: row[1] for row in result.fetchall()}
                
                logger.info(f"电影状态统计: {status_count}")
                return status_count
                
        except Exception as e:
            logger.error(f"获取状态统计失败: {e}")
            return {}
    
    async def close(self):
        """关闭数据库连接"""
        await self.engine.dispose()
        logger.info("数据库连接已关闭")