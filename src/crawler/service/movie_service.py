"""
电影服务模块

负责电影数据的查询、处理和URL构建等服务功能。
实现了从数据库查找ID间隔的电影记录和构建多语言电影URL的功能。
"""
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
import sqlite3
from loguru import logger

# 将项目根目录添加到 Python 路径
sys.path.append(str(Path(__file__).parent.parent.parent))

# 电影状态枚举
class CrawlerStatus:
    NEW = "NEW"           # 新添加，未爬取
    PROCESSING = "PROCESSING"  # 正在爬取中
    COMPLETED = "COMPLETED"    # 爬取完成
    FAILED = "FAILED"     # 爬取失败
    IGNORED = "IGNORED"   # 忽略此项

class MovieService:
    """
    电影服务类，提供电影数据查询和URL构建功能
    
    该服务实现了从数据库查找ID间隔的电影记录和构建多语言电影URL的功能，
    对应Java代码中的findMoviesWithIdGaps和getMissavLanguageUrl方法。
    """
    
    # MissAV基础URL
    BASE_URL_MISSAV = "https://missav.ai/"
    
    def __init__(self, db_path: str = "data/movies.db"):
        """
        初始化电影服务
        
        Args:
            db_path: SQLite数据库路径
        """
        self.db_path = db_path
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """确保数据库和表存在"""
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        # 连接数据库并创建表（如果不存在）
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建电影表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            title TEXT,
            status TEXT DEFAULT 'NEW',
            language TEXT DEFAULT 'ja',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_original_id ON movies(original_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_status ON movies(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code)')
        
        conn.commit()
        conn.close()
        
        logger.info(f"数据库初始化完成: {self.db_path}")
    
    async def find_movies_with_id_gaps(self, batch_size: int = 10) -> List[Dict[str, Any]]:
        """
        查找ID有间隔的电影记录
        
        这个方法实现了Java代码中的findMoviesWithIdGaps功能，
        查找状态为NEW的电影记录，优先考虑ID间隔的记录。
        
        Args:
            batch_size: 批量大小，默认为10
            
        Returns:
            电影记录列表，每个记录是一个字典
        """
        try:
            # 导入必要的模块
            from sqlalchemy import select, func, text
            from sqlalchemy.ext.asyncio import AsyncSession
            from app.config.database import async_session
            from common.db.entity.movie import Movie
            
            async with async_session() as session:
                # 1. 找出数据库中的最小和最大ID
                min_id_query = select(func.min(Movie.original_id).label('min_id'))
                min_id_result = await session.execute(min_id_query)
                min_id = min_id_result.scalar()
                
                max_id_query = select(func.max(Movie.original_id).label('max_id'))
                max_id_result = await session.execute(max_id_query)
                max_id = max_id_result.scalar()
                
                if min_id is None or max_id is None:
                    logger.info("数据库中没有找到电影ID")
                    return []
                
                # 2. 使用SQL查询找出状态为NEW的电影，优先考虑ID间隔
                # 使用原生SQL查询来实现复杂的WITH查询
                query = text("""
                WITH all_ids AS (
                    SELECT original_id FROM movies WHERE status = :status ORDER BY original_id
                ), id_gaps AS (
                    SELECT original_id FROM all_ids WHERE original_id NOT IN (
                        SELECT original_id FROM movies WHERE status != :status
                    )
                )
                SELECT * FROM movies WHERE original_id IN (SELECT original_id FROM id_gaps) AND status = :status 
                ORDER BY original_id ASC LIMIT :limit
                """)
                
                result = await session.execute(
                    query, 
                    {"status": CrawlerStatus.NEW, "limit": batch_size}
                )
                movies = [dict(row._mapping) for row in result.all()]
                
                if not movies:
                    # 如果没有找到ID间隔的电影，就直接按ID顺序查找
                    query = select(Movie).where(Movie.status == CrawlerStatus.NEW).order_by(Movie.original_id).limit(batch_size)
                    result = await session.execute(query)
                    movies = [dict(row._mapping) for row in result.all()]
                
                logger.info(f"找到 {len(movies)} 部状态为NEW的电影待处理")
                return movies
            
        except Exception as e:
            logger.error(f"查找ID间隔的电影时出错: {e}")
            logger.error(f"错误详情: {e}", exc_info=True)
            return []
    
    async def get_movies(self, status: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取电影列表
        
        Args:
            status: 按状态筛选
            limit: 返回的最大记录数
            
        Returns:
            电影记录列表，每个记录是一个字典
        """
        try:
            # 导入必要的模块
            from sqlalchemy import select
            from app.config.database import async_session
            from common.db.entity.movie import Movie
            
            async with async_session() as session:
                # 构建查询
                query = select(Movie)
                
                if status:
                    query = query.where(Movie.status == status)
                
                query = query.order_by(Movie.original_id.desc()).limit(limit)
                
                # 执行查询
                result = await session.execute(query)
                movies = [dict(row._mapping) for row in result.all()]
                
                return movies
            
        except Exception as e:
            logger.error(f"获取电影列表时出错: {e}")
            logger.error(f"错误详情: {e}", exc_info=True)
            return []
    
    def get_missav_language_url(self, dvd_code: str, language_code: str = "") -> str:
        """
        获取指定DVD代码和语言的MissAV URL
        
        这个方法实现了Java代码中的getMissavLanguageUrl功能，
        根据DVD代码和语言代码构建MissAV URL。
        
        Args:
            dvd_code: DVD代码，如'shmo-162'或'FC2-PPV-1020621'
            language_code: 语言代码，为空则使用默认语言
            
        Returns:
            完整的MissAV URL
        """
        if not language_code:
            return f"{self.BASE_URL_MISSAV}{dvd_code}"
        else:
            return f"{self.BASE_URL_MISSAV}{language_code}/{dvd_code}"
    
    def update_movie_status(self, movie_id: int, status: str) -> bool:
        """
        更新电影状态
        
        Args:
            movie_id: 电影ID
            status: 新状态
            
        Returns:
            是否更新成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "UPDATE movies SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, movie_id)
            )
            
            conn.commit()
            success = cursor.rowcount > 0
            
            if success:
                logger.info(f"电影ID {movie_id} 状态已更新为 {status}")
            else:
                logger.warning(f"未找到ID为 {movie_id} 的电影记录")
                
            return success
            
        except Exception as e:
            logger.error(f"更新电影状态时出错: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def add_movie(self, code: str, original_id: int, title: str = None, status: str = CrawlerStatus.NEW, language: str = "ja") -> int:
        """
        添加新电影记录
        
        Args:
            code: DVD代码
            original_id: 原始ID
            title: 电影标题
            status: 电影状态
            language: 语言代码
            
        Returns:
            新添加的电影ID，失败返回-1
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO movies (code, original_id, title, status, language) VALUES (?, ?, ?, ?, ?)",
                (code, original_id, title, status, language)
            )
            
            movie_id = cursor.lastrowid
            conn.commit()
            
            logger.info(f"添加了新电影: ID={movie_id}, 代码={code}, 原始ID={original_id}")
            return movie_id
            
        except Exception as e:
            logger.error(f"添加电影记录时出错: {e}")
            return -1
        finally:
            if 'conn' in locals():
                conn.close()


# 测试代码
if __name__ == "__main__":
    # 设置日志
    logger.add("logs/movie_service.log", rotation="10 MB", level="INFO")
    
    # 创建服务实例
    service = MovieService("data/test_movies.db")
    
    # 添加一些测试数据
    for i in range(1, 21):
        code = f"TEST-{i:03d}"
        service.add_movie(code, i)
    
    # 将一些电影标记为已完成，创造ID间隔
    for i in [2, 5, 8, 11, 14, 17]:
        service.update_movie_status(i, CrawlerStatus.COMPLETED)
    
    # 测试查找ID间隔的电影
    movies = service.find_movies_with_id_gaps(5)
    logger.info(f"找到的电影: {movies}")
    
    # 测试URL构建
    for movie in movies[:2]:
        url = service.get_missav_language_url(movie['code'])
        logger.info(f"电影 {movie['code']} 的URL: {url}")
        
        url_ja = service.get_missav_language_url(movie['code'], "ja")
        logger.info(f"电影 {movie['code']} 的日语URL: {url_ja}")
