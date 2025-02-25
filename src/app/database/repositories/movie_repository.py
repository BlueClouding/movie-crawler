from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.models.movie import Movie, MovieTitle
from database.models.enums import SupportedLanguage
from database.repositories.base_repository import BaseRepository

class MovieRepository(BaseRepository[Movie]):
    def __init__(self):
        super().__init__(Movie)
    
    def get_by_code(self, db: Session, *, code: str) -> Optional[Movie]:
        """根据影片代码获取影片"""
        return db.query(Movie).filter(Movie.code == code).first()
    
    def get_with_titles(
        self, db: Session, *, skip: int = 0, limit: int = 100, language: SupportedLanguage = None
    ) -> List[Movie]:
        """获取影片列表，包含标题"""
        query = db.query(Movie)
        if language:
            query = query.join(MovieTitle).filter(MovieTitle.language == language)
        return query.order_by(Movie.release_date.desc()).offset(skip).limit(limit).all()
    
    def search_by_title(
        self, db: Session, *, title: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """根据标题搜索影片"""
        query = db.query(Movie).join(MovieTitle)
        
        if language:
            query = query.filter(MovieTitle.language == language)
        
        query = query.filter(MovieTitle.title.ilike(f"%{title}%"))
        return query.order_by(Movie.release_date.desc()).offset(skip).limit(limit).all()
    
    def get_by_actress(
        self, db: Session, *, actress_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """获取演员的所有影片"""
        return (
            db.query(Movie)
            .join(Movie.actresses)
            .filter(Movie.actresses.any(id=actress_id))
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def get_by_genre(
        self, db: Session, *, genre_id: int, skip: int = 0, limit: int = 100
    ) -> List[Movie]:
        """获取特定类型的所有影片"""
        return (
            db.query(Movie)
            .join(Movie.genres)
            .filter(Movie.genres.any(id=genre_id))
            .order_by(Movie.release_date.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
    
    def create_with_relations(
        self, 
        db: Session, 
        *, 
        movie_data: Dict[str, Any],
        titles: List[Dict[str, Any]] = None,
        actress_ids: List[int] = None,
        genre_ids: List[int] = None
    ) -> Movie:
        """创建影片及其关联数据"""
        # 创建影片
        db_movie = Movie(**movie_data)
        db.add(db_movie)
        db.flush()  # 获取ID但不提交
        
        # 添加标题
        if titles:
            for title_data in titles:
                db_title = MovieTitle(**title_data, movie_id=db_movie.id)
                db.add(db_title)
        
        # 添加演员关联
        if actress_ids:
            from database.models.actress import Actress
            actresses = db.query(Actress).filter(Actress.id.in_(actress_ids)).all()
            db_movie.actresses = actresses
        
        # 添加类型关联
        if genre_ids:
            from database.models.genre import Genre
            genres = db.query(Genre).filter(Genre.id.in_(genre_ids)).all()
            db_movie.genres = genres
        
        db.commit()
        db.refresh(db_movie)
        return db_movie