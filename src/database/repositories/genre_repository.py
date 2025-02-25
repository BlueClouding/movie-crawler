from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.genre import Genre, GenreName
from app.models.enums import SupportedLanguage
from app.repositories.base_repository import BaseRepository

class GenreRepository(BaseRepository[Genre]):
    def __init__(self):
        super().__init__(Genre)
    
    def get_by_name(
        self, db: Session, *, name: str, language: SupportedLanguage = None
    ) -> Optional[Genre]:
        """根据名称获取类型"""
        query = db.query(Genre).join(GenreName)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        return query.filter(GenreName.name == name).first()
    
    def search_by_name(
        self, db: Session, *, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """根据名称搜索类型"""
        query = db.query(Genre).join(GenreName)
        
        if language:
            query = query.filter(GenreName.language == language)
        
        query = query.filter(GenreName.name.ilike(f"%{name}%"))
        return query.offset(skip).limit(limit).all()
    
    def create_with_names(
        self, db: Session, *, names: List[Dict[str, Any]], urls: List[str] = None
    ) -> Genre:
        """创建类型及其多语言名称"""
        # 创建类型
        db_genre = Genre(urls=urls or [])
        db.add(db_genre)
        db.flush()  # 获取ID但不提交
        
        # 添加名称
        for name_data in names:
            db_name = GenreName(**name_data, genre_id=db_genre.id)
            db.add(db_name)
        
        db.commit()
        db.refresh(db_genre)
        return db_genre
    
    def get_popular(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Genre]:
        """获取最受欢迎的类型（根据影片数量）"""
        from sqlalchemy import func
        from app.models.movie import movie_genres
        
        # 获取类型ID和影片数量
        genre_counts = (
            db.query(
                movie_genres.c.genre_id,
                func.count(movie_genres.c.movie_id).label("movie_count")
            )
            .group_by(movie_genres.c.genre_id)
            .subquery()
        )
        
        # 查询类型并按影片数量排序
        return (
            db.query(Genre)
            .join(
                genre_counts,
                Genre.id == genre_counts.c.genre_id
            )
            .order_by(genre_counts.c.movie_count.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )