import logging
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, insert, func
from app.repositories.genre_repository import GenreRepository
from fastapi import Depends
from common.db.entity.crawler import CrawlerProgress
from common.db.entity.genre import Genre
from common.db.entity.crawler import PagesProgress
from crawler.repository.crawler_progress_repository import CrawlerProgressRepository
from crawler.repository.page_crawler_repository import PageCrawlerRepository
from crawler.repository.movie_crawler_repository import MovieCrawlerRepository
from crawler.models.update_progress import GenrePageProgressUpdate
from common.db.entity.crawler import VideoProgress
from common.enums.enums import CrawlerStatus
class CrawlerProgressService:
    """Database progress manager."""
    
    def __init__(self, genre_repository: GenreRepository = Depends(GenreRepository),
        page_crawler_repository: PageCrawlerRepository = Depends(PageCrawlerRepository), 
        movie_crawler_repository: MovieCrawlerRepository = Depends(MovieCrawlerRepository),
        crawler_progress_repository: CrawlerProgressRepository = Depends(CrawlerProgressRepository)
    ):
        """Initialize progress manager.
        
        Args:
            genre_repository: GenreRepository instance for genre operations
            page_crawler_repository: PageCrawlerRepository instance for page operations
            movie_crawler_repository: MovieCrawlerRepository instance for movie operations
            crawler_progress_repository: CrawlerProgressRepository instance for progress operations
        """
        self._logger = logging.getLogger(__name__)
        self._genre_repository : GenreRepository = genre_repository
        self._page_crawler_repository : PageCrawlerRepository = page_crawler_repository
        self._movie_crawler_repository : MovieCrawlerRepository = movie_crawler_repository
        self._crawler_progress_repository : CrawlerProgressRepository = crawler_progress_repository

    async def create_crawler_progress(self, crawler_progress: CrawlerProgress):
        return await self._crawler_progress_repository.create(crawler_progress)

    async def get_genre_progress(self, genre_id: int, code: str = None, task_id: int = None) -> int:
        """Get the last processed page for a genre.

        Args:
            genre_id: ID of the genre
            code: Optional code of the genre

        Returns:
            int: Last processed page number, 0 if not started
        """
       
        try:
            # Query genres table for the matching code
            db_genre = await self._genre_repository.get_by_code(code)
            if db_genre:
                # If found matching genre, use its ID for progress lookup
                self._logger.info(f"Found genre with code {code}, id: {db_genre.id}")
                genre_id = db_genre.id
        except Exception as code_error:
            self._logger.error(f"Error querying genre by code: {str(code_error)}")
            return 0
    
        # Query progress using genre_id
        return await self._page_crawler_repository.get_latest_page_by_genre_task(genre_id, task_id)
    

    #返回值为最新的genre_progress 的 id
    async def update_genre_progress(self, genre_id: int, page: int, total_pages: int, 
    code: str = None, status: str = None, total_items: int = None, task_id: int = None):
        """Update progress for a genre.

        Args:
            genre_id: ID of the genre
            page: Current page number
            total_pages: Total number of pages
            code: Optional code of the genre
            status: Optional status of the genre
            total_items: Optional total number of items
        """
        try:
            # 如果提供了 code，则尝试使用 code 查询
            if code:
                try:
                    # 查询 genres 表中是否有匹配的 code
                    db_genre = await self._genre_repository.get_by_code(code)
                    if db_genre:
                        # 如果找到了匹配的 genre，则使用其 ID
                        self._logger.info(f"Found genre with code {code}, id: {db_genre.id}")
                        genre_id = db_genre.id
                except Exception as e:
                    self._logger.error(f"Error querying genre by code: {str(e)}")
            
            # First query existing progress
            page_progress : PagesProgress = await self._page_crawler_repository.get_latest_page_by_genre_task(genre_id, task_id)

            if page_progress:
                update_values = GenrePageProgressUpdate(
                    page=page, total_pages=total_pages, code=code, status=status, total_items=total_items
                )
                # Update the progress record
                return await self._page_crawler_repository.update_page_progress(page_progress.id, update_values)
            else:
                # Create new progress
                page_progress = PagesProgress(
                    crawler_progress_id=task_id,
                    relation_id=genre_id,
                    page_type='genre',
                    page_number=page,
                    total_pages=total_pages,
                    total_items=total_items,
                    status=status
                )
                return await self._page_crawler_repository.create_genre_progress(page_progress)
        except Exception as e:
            self._logger.error(f"Error updating genre progress: {str(e)}")
            return None

    async def create_genre_progress(self, genre_id: int, page: int, total_pages: int, code: str = None, status: str = None, total_items: int = None, task_id: int = None):
        """Create new progress for a genre.

        Args:
            genre_id: ID of the genre
            page: Current page number
            total_pages: Total number of pages
            code: Optional code of the genre (may be used for logging or future lookups)
            status: Optional status of the genre
            total_items: Optional total number of items
            
        Returns:
            int: ID of the created progress record, or None if failed
        """
        try:
            # Query genres table for logging purposes
            db_genre : Genre = await self._genre_repository.get_by_code(code)
            if db_genre:
                self._logger.info(f"Creating genre progress for code {code}, id: {db_genre.id}")

                result = await self._page_crawler_repository.create_genre_progress(
                    PagesProgress(
                        crawler_progress_id=task_id,
                        relation_id=genre_id,
                        page_type='genre',
                        page_number=page,
                        total_pages=total_pages,
                        total_items=total_items,
                        status=status
                    )
                )
                return result
            else:
                self._logger.warning(f"Genre with code {code} not found in genres table, creating progress with provided genre_id: {genre_id}")
        except Exception as code_error:
            self._logger.error(f"Error querying genre by code during create progress: {str(code_error)}")
            return None

    async def update_page_progress(self, page_progress_id: int, status: str, processed_items: int = None):
        """Update page progress status and processed items count.
        
        Args:
            page_progress_id: ID of the page progress record
            status: New status
            processed_items: Number of items processed
        """
        try:
            # Prepare update values
            update_values = GenrePageProgressUpdate(status=status)     
            # Execute update
            await self._page_crawler_repository.update_page_progress(page_progress_id, update_values)
            
            self._logger.info(f"Updated page progress {page_progress_id} to status '{status}'")
            return True
        except Exception as e:
            self._logger.error(f"Error updating page progress: {str(e)}")
            return False
            
    async def update_task_status(self, task_id: int, status: str):
        """Update task status.
        
        Args:
            task_id: Task ID
            status: New status
        """
        try:
            # 创建一个新的CrawlerProgress对象，只包含ID和状态
            progress = CrawlerProgress(id=task_id, status=status)
            # 调用repository的update_status方法更新状态
            result = await self._crawler_progress_repository.update_status(progress)
            if result:
                self._logger.info(f"成功更新任务状态: 任务ID={task_id}, 状态={status}")
            else:
                self._logger.warning(f"无法更新任务状态: 任务ID={task_id}, 状态={status}")
            return result
        except Exception as e:
            # 记录错误但不重新抛出，避免影响调用者
            self._logger.error(f"Error updating task status: {str(e)}")
            return None
        
    async def clear_progress(self, task_id: int):
        try:
            # Delete all progress records
            await self._page_crawler_repository.db.execute(delete(PagesProgress))
            await self._movie_crawler_repository.db.execute(delete(VideoProgress))
            await self._crawler_progress_repository.db.commit()
        except Exception as e:
            await self._crawler_progress_repository.db.rollback()
            self._logger.error(f"Error clearing progress: {str(e)}")
            
    async def save_movie(self, movie_data: dict):
        """Save movie data to database.
        
        Args:
            movie_data: Dictionary containing movie information
        """
            
        try:
            # 确保必要的字段存在
            if 'url' not in movie_data:
                self._logger.warning("Movie data missing URL, skipping")
                return
                
            # 从 URL 中提取电影代码
            code = movie_data.get('code', '')
            if not code:
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
            
            # 获取其他电影信息
            link = movie_data.get('link', '')
            original_id = movie_data.get('id', None)  # 从movie_data中获取原始ID
            duration = movie_data.get('duration', '00:00:00')
            thumbnail = movie_data.get('thumbnail', '')
            
            # 直接执行插入操作，不使用嵌套事务
            # 构建Movie表的插入数据
            movie_insert = insert(Movie).values(
                code=code,
                title=title,
                duration=duration,
                thumbnail=thumbnail,
                link=link,
                original_id=int(original_id) if original_id else 0,
                release_date='',
                status=MovieStatus.NEW.value,
            )
            
            # 执行插入并获取返回的ID
            result = await self._movie_crawler_repository.db.execute(movie_insert)
            movie_id = result.inserted_primary_key[0]
            
            self._logger.info(f"Inserted into Movie table with ID: {movie_id}")
            
            # 然后插入到VideoProgress表
            video_progress_insert = insert(VideoProgress).values(
                crawler_progress_id=self._task_id,
                genre_id=movie_data['genre_id'],
                page_number=movie_data['page_number'],
                title=title,
                url=movie_data['url'],
                code=code,
                movie_id=movie_id,
                status=CrawlerStatus.PENDING.value,
                page_progress_id=movie_data['page_progress_id']
            )
            
            await self._movie_crawler_repository.db.execute(video_progress_insert)
            
            # 提交事务
            await self._movie_crawler_repository.db.commit()
            self._logger.info(f"Saved movie: {title} ({code}) with ID: {movie_id}")
            return movie_id
        except Exception as e:
            # 确保回滚事务
            try:
                await self._movie_crawler_repository.db.rollback()
            except Exception as rollback_e:
                self._logger.error(f"Error during rollback: {str(rollback_e)}")
            
            self._logger.error(f"Error saving movie: {str(e)}")
            return None
            
    async def get_pending_movies(self, task_id:int, limit: int = 100):
        """获取待处理的电影列表。
        
        Args:
            limit: 最大返回数量，默认100条
            
        Returns:
            list: 待处理电影列表
        """
        if not self._movie_crawler_repository.db:
            return []
            
        try:
            # 查询状态为“pending”且detail_fetched为False的电影记录
            result = await self._movie_crawler_repository.db.execute(
                select(VideoProgress)
                .where(
                    VideoProgress.crawler_progress_id == task_id,
                    VideoProgress.status == CrawlerStatus.PENDING.value,
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
                    "retry_count": movie.retry_count,
                    "original_id": movie.movie_id
                })
                
            self._logger.info(f"Found {len(movie_list)} pending movies")
            return movie_list
        except Exception as e:
            self._logger.error(f"Error getting pending movies: {str(e)}")
            return []
            
    #增加更新page_progress
    async def update_movie_status(self, movie_id: int, status: str, error: str = None):
        """更新电影的处理状态。
        
        Args:
            movie_id: 电影ID
            status: 新状态，如 'completed', 'error', 'pending'
            error: 错误信息（如果有）
        """
        if not movie_id:
            return
            
        try:
            # 准备更新数据
            update_data = {
                "status": status
            }
            
            # 如果状态为"completed"，设置detail_fetched为True
            if status == "completed":
                update_data["detail_fetched"] = True
                
            # 如果提供了错误信息，更新last_error字段并增加retry_count
            if error:
                update_data["last_error"] = error
                update_data["retry_count"] = VideoProgress.retry_count + 1
                
            
                # 首先获取电影记录，以获取page_progress_id
                video_result = await self._movie_crawler_repository.db.execute(
                    select(VideoProgress).where(VideoProgress.movie_id == movie_id)
                )
                video_progress = video_result.scalar_one_or_none()
                    
                if not video_progress:
                    self._logger.error(f"Video progress not found for movie_id {movie_id}")
                    return
                        
                page_progress_id = video_progress.page_progress_id
                    
                # 使用独立会话执行更新
                await self._movie_crawler_repository.db.execute(
                    update(VideoProgress)
                    .where(VideoProgress.movie_id == movie_id)
                    .values(**update_data)
                )
                    
                # 如果状态为已完成，检查并更新对应的pages_progress记录
                if status == "completed" and page_progress_id:
                    # 获取页面进度记录
                    page_result = await self._movie_crawler_repository.db.execute(
                        select(PagesProgress).where(PagesProgress.id == page_progress_id)
                    )
                    page_progress = page_result.scalar_one_or_none()
                        
                    if page_progress:
                            # 获取当前页面已完成的电影数量
                            count_result = await self._movie_crawler_repository.db.execute(
                                select(func.count())
                                .select_from(VideoProgress)
                                .where(
                                    VideoProgress.page_progress_id == page_progress_id,
                                    VideoProgress.status == "completed"
                                )
                            )
                            completed_count = count_result.scalar_one()
                            
                            # 获取当前页面的总电影数量
                            total_count_result = await self._movie_crawler_repository.db.execute(
                                select(func.count())
                                .select_from(VideoProgress)
                                .where(VideoProgress.page_progress_id == page_progress_id)
                            )
                            total_count = total_count_result.scalar_one()
                            
                            # 更新页面进度记录
                            page_update_data = {
                                "processed_items": completed_count,
                                "total_items": total_count
                            }
                            
                            # 如果已完成的电影数量等于总数，则将页面状态设置为已完成
                            if completed_count >= total_count:
                                page_update_data["status"] = "completed"
                                self._logger.info(f"All movies for page_progress_id {page_progress_id} have been completed")
                            
                            await self._movie_crawler_repository.db.execute(
                                update(PagesProgress)
                                .where(PagesProgress.id == page_progress_id)
                                .values(**page_update_data)
                            )
                
                self._logger.info(f"Updated movie {movie_id} status to {status}")
                return True
        except Exception as e:
            self._logger.error(f"Error updating movie status: {str(e)}")
            return False
            
    async def get_actresses_to_process(self, limit: int = 50):
        """获取待处理的女演员列表。
        
        Args:
            limit: 最大返回数量，默认50条
            
        Returns:
            list: 待处理女演员列表
        """
           
        try:
            # 这里需要根据实际的数据库结构进行查询
            # 例如，我们可能需要查询已经处理过的电影中提取的女演员信息
            # 并返回那些尚未处理详细信息的女演员
            
            # 示例实现（需要根据实际情况调整）
            from common.db.entity.actress import Actress, ActressName
            
            # 查询女演员及其名称
            result = await self._movie_crawler_repository.db.execute(
                select(Actress, ActressName)
                .join(ActressName, Actress.id == ActressName.actress_id)
                .limit(limit)
            )
            
            actresses = result.scalars().all()
            
            # 将数据库记录转换为字典列表
            actress_list = []
            for actress, actressName in actresses:
                # 构造女演员URL（假设有这个格式）
                # 注意：实际URL格式可能需要根据网站结构调整
                url = f"http://123av.com/ja/actress/{actress.id}"
                
                actress_list.append({
                    "id": actress.id,
                    "name": actressName.name,
                    "url": url,
                })
                
            self._logger.info(f"Found {len(actress_list)} actresses to process")
            return actress_list
        except Exception as e:
            self._logger.error(f"Error getting actresses to process: {str(e)}")
            return []


    #通过page_progress_id表获 video_progress已经处理的电影总量
    async def get_processed_movies_count(self, page_progress_id: int) -> int:
        try:    
            result = await self._movie_crawler_repository.db.execute(
                select(VideoProgress)
                .where(VideoProgress.page_progress_id == page_progress_id)
                .where(VideoProgress.status == CrawlerStatus.COMPLETED.value)
            )
            return result.scalar()
        except Exception as e:
            self._logger.error(f"Error getting processed movies count: {str(e)}")
            return 0