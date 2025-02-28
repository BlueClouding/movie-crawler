from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.entity.actress import Actress, ActressName
from app.db.entity.enums import SupportedLanguage
from app.db.entity.movie_actress import MovieActress
from app.repositories.base_repository import BaseRepository

class ActressRepository(BaseRepository[Actress]):
    def __init__(self):
        super().__init__(Actress)
    
    async def get_by_name(
        self, db: AsyncSession, *, name: str, language: SupportedLanguage = None
    ) -> Optional[Actress]:
        """根据名字获取演员"""
        query = select(Actress).join(ActressName)
        
        if language:
            query = query.where(ActressName.language == language)
        
        query = query.where(ActressName.name == name)
        result = await db.execute(query)
        return result.scalars().first()
    
    async def search_by_name(
        self, db: AsyncSession, *, name: str, language: SupportedLanguage = None, skip: int = 0, limit: int = 100
    ) -> List[Actress]:
        """根据名字搜索演员"""
        query = select(Actress).join(ActressName)
        
        if language:
            query = query.where(ActressName.language == language)
        
        query = query.where(ActressName.name.ilike(f"%{name}%"))
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def create_with_names(
        self, db: AsyncSession, *, names: List[Dict[str, Any]]
    ) -> Actress:
        """创建演员及其多语言名称"""
        # 创建演员
        db_actress = Actress()
        db.add(db_actress)
        await db.flush()  # 获取ID但不提交
        
        # 添加名称
        for name_data in names:
            db_name = ActressName(**name_data, actress_id=db_actress.id)
            db.add(db_name)
        
        await db.commit()
        await db.refresh(db_actress)
        return db_actress
    
    async def get_popular(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Actress]:
        """获取最受欢迎的演员（根据影片数量）"""
        # 获取演员ID和影片数量的子查询
        subquery = (
            select(
                MovieActress.actress_id,
                func.count(MovieActress.movie_id).label("movie_count")
            )
            .group_by(MovieActress.actress_id)
            .subquery()
        )
        
        # 查询演员并按影片数量排序
        query = (
            select(Actress)
            .join(
                subquery,
                Actress.id == subquery.c.actress_id
            )
            .order_by(subquery.c.movie_count.desc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        return result.scalars().all()