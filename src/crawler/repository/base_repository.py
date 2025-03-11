from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Type, TypeVar
from fastapi import Depends
from sqlalchemy.orm import lazyload
from app.config.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, insert

M = TypeVar("M")  # 模型类型
K = TypeVar("K")  # 主键类型

class BaseRepository(Generic[M, K], ABC):
    def __init__(self, db: AsyncSession = Depends(get_db_session())):
        self.db = db
        self.model: Type[M] = self.__class__.__orig_bases__[0].__args__[0]  # 自动获取泛型类型[1](@ref)
    
    async def list(self, 
        filters: Optional[dict] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> List[M]:
        """通用分页查询方法"""
        query = select(self.model)
        if filters:
            query = query.filter_by(**filters)
        result = await self.db.execute(query.offset(offset).limit(limit))
        return result.scalars().all()
    
    async def create(self, instance: M) -> M:
        """通用创建方法"""
        await self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: K, update_data: dict) -> M:
        """通用更新方法"""
        instance = await self.db.execute(select(self.model).where(self.model.id == id)).scalar_one()
        for key, value in update_data.items():
            setattr(instance, key, value)
        await self.db.commit()
        return instance

    async def delete(self, id: K) -> None:
        """通用删除方法"""
        instance = await self.db.execute(select(self.model).where(self.model.id == id)).scalar_one()
        await self.db.delete(instance)
        await self.db.commit()