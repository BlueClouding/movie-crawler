import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, insert
from app.db.entity.crawler import CrawlerProgress, PagesProgress, VideoProgress
from app.repositories.genre_repository import GenreRepository

class DBProgressManager:
    """Database progress manager."""
    
    def __init__(self, language: str, task_id: int):
        """Initialize progress manager.
        
        Args:
            language: Language code
            task_id: ID of the associated crawler task
        """
        self._language = language
        self._session = None
        self._logger = logging.getLogger(__name__)
        self._task_id = task_id
        self._genre_repository = GenreRepository()

    async def initialize(self, session: AsyncSession):
        """Initialize crawler progress record.
        
        Args:
            session: SQLAlchemy async session
        """
        self._session = session

    async def get_genre_progress(self, genre_id: int, code: str = None) -> int:
        """Get the last processed page for a genre.

        Args:
            genre_id: ID of the genre
            code: Optional code of the genre

        Returns:
            int: Last processed page number, 0 if not started
        """
        if not self._session:
            return 0
            
        try:
            # 如果提供了 code，则尝试使用 code 查询
            if code:
                try:
                    # 查询 genres 表中是否有匹配的 code
                    db_genre = await self._genre_repository.get_by_code(self._session, code=code)
                    if db_genre:
                        # 如果找到了匹配的 genre，则使用其 ID 查询进度
                        self._logger.info(f"Found genre with code {code}, id: {db_genre.id}")
                        genre_id = db_genre.id
                except Exception as e:
                    self._logger.error(f"Error querying genre by code: {str(e)}")
            
            # 使用 genre_id 查询进度
            result = await self._session.execute(
                select(PagesProgress)
                .filter(
                    PagesProgress.relation_id == genre_id,
                    PagesProgress.page_type == 'genre'
                )
                .order_by(PagesProgress.page_number.desc())
                .limit(1)
            )
            page_progress = result.scalars().first()
            return page_progress.page_number if page_progress else 0
        except Exception as e:
            self._logger.error(f"Error getting genre progress: {str(e)}")
            return 0

    async def update_genre_progress(self, genre_id: int, page: int, total_pages: int, code: str = None):
        """Update progress for a genre.

        Args:
            genre_id: ID of the genre
            page: Current page number
            total_pages: Total number of pages
            code: Optional code of the genre
        """
        if not self._session:
            return
            
        try:
            # 如果提供了 code，则尝试使用 code 查询
            if code:
                try:
                    # 查询 genres 表中是否有匹配的 code
                    db_genre = await self._genre_repository.get_by_code(self._session, code=code)
                    if db_genre:
                        # 如果找到了匹配的 genre，则使用其 ID
                        self._logger.info(f"Found genre with code {code}, id: {db_genre.id}")
                        genre_id = db_genre.id
                except Exception as e:
                    self._logger.error(f"Error querying genre by code: {str(e)}")
            
            # First query existing progress
            result = await self._session.execute(
                select(PagesProgress)
                .filter(
                    PagesProgress.relation_id == genre_id,
                    PagesProgress.page_type == 'genre',
                    PagesProgress.crawler_progress_id == self._task_id
                )
            )
            page_progress = result.scalars().first()
            
            if page_progress:
                # Update existing progress
                await self._session.execute(
                    update(PagesProgress)
                    .where(PagesProgress.id == page_progress.id)
                    .values(
                        page_number=page,
                        total_pages=total_pages,
                        status='completed' if page >= total_pages else 'processing'
                    )
                )
            else:
                # Create new progress
                page_progress = PagesProgress(
                    crawler_progress_id=self._task_id,
                    relation_id=genre_id,
                    page_type='genre',
                    page_number=page,
                    total_pages=total_pages,
                    status='completed' if page >= total_pages else 'processing'
                )
                self._session.add(page_progress)
                
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error updating genre progress: {str(e)}")

    async def get_detail_progress(self, genre_id: int) -> int:
        """Get the number of processed movies for a genre.

        Args:
            genre_id (int): ID of the genre

        Returns:
            int: Number of processed movies
        """
        if not self._crawler_progress:
            return 0

        try:
            page_progress = await self._crawler_db.get_pages_progress(
                self._crawler_progress.id,
                genre_id
            )
            return page_progress.processed_items if page_progress else 0
        except Exception as e:
            self._logger.error(f"Error getting detail progress: {str(e)}")
            return 0

    async def update_detail_progress(self, genre_id: int, processed: int, total: int):
        """Update the number of processed movies for a genre.

        Args:
            genre_id (int): ID of the genre
            processed (int): Number of processed movies
            total (int): Total number of movies
        """
        if not self._crawler_progress:
            return

        try:
            await self._crawler_db.update_pages_progress(
                self._crawler_progress.id,
                genre_id,
                processed_items=processed,
                total_items=total
            )
        except Exception as e:
            self._logger.error(f"Error updating detail progress: {str(e)}")

    async def is_genre_completed(self, genre_id: int) -> bool:
        """Check if a genre is completed.

        Args:
            genre_id (int): ID of the genre

        Returns:
            bool: True if genre is completed
        """
        if not self._crawler_progress:
            return False

        try:
            page_progress = await self._crawler_db.get_pages_progress(
                self._crawler_progress.id,
                genre_id
            )
            if not page_progress:
                return False
                
            return (
                page_progress.status == "completed" or
                (page_progress.page_number >= page_progress.total_pages and
                 page_progress.processed_items >= page_progress.total_items)
            )
        except Exception as e:
            self._logger.error(f"Error checking genre completion: {str(e)}")
            return False
            
    async def update_task_status(self, task_id: int, status: str, message: Optional[str] = None):
        """Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            message: Optional status message
        """
        if not self._session:
            return
            
        try:
            await self._session.execute(
                update(CrawlerProgress)
                .where(CrawlerProgress.id == task_id)
                .values(status=status)
            )
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error updating task status: {str(e)}")
            
    async def clear_progress(self):
        """Clear all progress data for current language."""
        if not self._session:
            return
            
        try:
            # Delete all progress records
            await self._session.execute(delete(PagesProgress))
            await self._session.execute(delete(VideoProgress))
            await self._session.commit()
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error clearing progress: {str(e)}")
            
    async def save_movie(self, movie_data: dict):
        """Save movie data to database.
        
        Args:
            movie_data: Dictionary containing movie information
        """
        if not self._session or not movie_data:
            return
            
        try:
            # 确保必要的字段存在
            if 'url' not in movie_data:
                self._logger.warning("Movie data missing URL, skipping")
                return
                
            # 从 URL 中提取电影代码
            code = ''
            import re
            code_match = re.search(r'/([A-Z]+-\d+)', movie_data.get('url', ''))
            if code_match:
                code = code_match.group(1)
            else:
                # 如果无法从 URL 提取代码，尝试使用 URL 的最后一部分
                path_parts = movie_data.get('url', '').split('/')
                if path_parts and path_parts[-1]:
                    code = path_parts[-1]
            
            # 处理缺失的标题
            title = movie_data.get('title', '')
            if not title:
                # 如果标题为空，使用代码作为标题
                title = code
            
            # Insert movie data into the database
            await self._session.execute(
                insert(VideoProgress).values(
                    crawler_progress_id=self._task_id,
                    genre_id=movie_data['genre_id'],
                    page_number=movie_data['page_number'],
                    title=title,
                    url=movie_data['url'],
                    code=code
                )
            )
            await self._session.commit()
            self._logger.info(f"Saved movie: {title} ({code})")
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error saving movie: {str(e)}")
            
    async def get_pending_movies(self, limit: int = 100):
        """获取待处理的电影列表。
        
        Args:
            limit: 最大返回数量，默认100条
            
        Returns:
            list: 待处理电影列表
        """
        if not self._session:
            return []
            
        try:
            # 查询状态为“pending”且detail_fetched为False的电影记录
            result = await self._session.execute(
                select(VideoProgress)
                .where(
                    VideoProgress.crawler_progress_id == self._task_id,
                    VideoProgress.status == "pending",
                    VideoProgress.detail_fetched == False
                )
                .limit(limit)
            )
            
            movies = result.scalars().all()
            
            # 将数据库记录转换为字典列表
            movie_list = []
            for movie in movies:
                movie_list.append({
                    "id": movie.id,
                    "code": movie.code,
                    "url": movie.url,
                    "genre_id": movie.genre_id,
                    "page_number": movie.page_number,
                    "title": movie.title,
                    "status": movie.status,
                    "retry_count": movie.retry_count
                })
                
            self._logger.info(f"Found {len(movie_list)} pending movies")
            return movie_list
        except Exception as e:
            self._logger.error(f"Error getting pending movies: {str(e)}")
            return []
            
    async def update_movie_status(self, movie_id: int, status: str, error: str = None):
        """更新电影的处理状态。
        
        Args:
            movie_id: 电影ID
            status: 新状态，如 'completed', 'error', 'pending'
            error: 错误信息（如果有）
        """
        if not self._session or not movie_id:
            return
            
        try:
            # 准备更新数据
            update_data = {
                "status": status
            }
            
            # 如果状态为“completed”，设置detail_fetched为True
            if status == "completed":
                update_data["detail_fetched"] = True
                
            # 如果提供了错误信息，更新last_error字段并增加retry_count
            if error:
                update_data["last_error"] = error
                update_data["retry_count"] = VideoProgress.retry_count + 1
            
            # 执行更新
            await self._session.execute(
                update(VideoProgress)
                .where(VideoProgress.id == movie_id)
                .values(**update_data)
            )
            await self._session.commit()
            
            self._logger.info(f"Updated movie {movie_id} status to {status}")
        except Exception as e:
            await self._session.rollback()
            self._logger.error(f"Error updating movie status: {str(e)}")
            
    async def get_actresses_to_process(self, limit: int = 50):
        """获取待处理的女演员列表。
        
        Args:
            limit: 最大返回数量，默认50条
            
        Returns:
            list: 待处理女演员列表
        """
        # 注意：这个方法的实现可能需要根据实际的数据库结构进行调整
        # 这里我们假设有一个存储女演员处理状态的表或字段
        
        if not self._session:
            return []
            
        try:
            # 这里需要根据实际的数据库结构进行查询
            # 例如，我们可能需要查询已经处理过的电影中提取的女演员信息
            # 并返回那些尚未处理详细信息的女演员
            
            # 示例实现（需要根据实际情况调整）
            from app.db.entity.actress import Actress, ActressName
            
            # 查询女演员及其名称
            result = await self._session.execute(
                select(Actress, ActressName)
                .join(ActressName, Actress.id == ActressName.actress_id)
                .where(Actress.detail_fetched == False)  # 假设有这个字段
                .limit(limit)
            )
            
            actresses = result.all()
            
            # 将数据库记录转换为字典列表
            actress_list = []
            for actress, name in actresses:
                # 构造女演员URL（假设有这个格式）
                # 注意：实际URL格式可能需要根据网站结构调整
                url = f"http://123av.com/{self._language}/actress/{actress.id}"
                
                actress_list.append({
                    "id": actress.id,
                    "name": name.name,
                    "url": url
                })
                
            self._logger.info(f"Found {len(actress_list)} actresses to process")
            return actress_list
        except Exception as e:
            self._logger.error(f"Error getting actresses to process: {str(e)}")
            return []
