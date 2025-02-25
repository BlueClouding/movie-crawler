from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.actress import Actress, ActressName
from app.models.enums import SupportedLanguage
from app.repositories.base_repository import BaseRepository

class ActressRepository(BaseRepository[Actress]):
    def __init__(self):
        super().__init__(Actress)
    
    def get_by_name(
        self, db: Session, *, name: str, language: SupportedLanguage = None
    ) -> Optional[Actress]:
        """根据名字获取演员"""
        query = db.query(Actress).join(ActressName)
        
        if language:
            query = query.filter(ActressName.language == language)
        
        return query.filter(ActressName.name == name).first()
    
    def search_by_name(
        self, db: Session, *, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Actress]:
        """根据名字搜索演员"""
        query = db.query(Actress).join(ActressName)
        
        if language:
            query = query.filter(ActressName.language == language)
        
        query = query.filter(ActressName.name.ilike(f"%{name}%"))
        return query.offset(skip).limit(limit).all()
    
    def create_with_names(
        self, db: Session, *, names: List[Dict[str, Any]]
    ) -> Actress:
        """创建演员及其多语言名称"""
        # 创建演员
        db_actress = Actress()
        db.add(db_actress)
        db.flush()  # 获取ID但不提交
        
        # 添加名称
        for name_data in names:
            db_name = ActressName(**name_data, actress_id=db_actress.id)
            db.add(db_name)
        
        db.commit()
        db.refresh(db_actress)
        return db_actress
    
    def get_popular(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Actress]:
        """获取最受欢迎的演员（根据影片数量）"""
        from sqlalchemy import func
        from app.models.movie import movie_actresses
        
        # 获取演员ID和影片数量
        actress_counts = (
            db.query(
                movie_actresses.c.actress_id,
                func.count(movie_actresses.c.movie_id).label("movie_count")
            )
            .group_by(movie_actresses.c.actress_id)
            .subquery()
        )
        
        # 查询演员并按影片数量排序
        return (
            db.query(Actress)
            .join(
                actress_counts,
                Actress.id == actress_counts.c.actress_id
            )
            .order_by(actress_counts.c.movie_count.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )