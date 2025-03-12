# 基础异步Repository抽象类
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from typing import Generic, List, Optional, Type, TypeVar
from sqlalchemy import select
from app.config.database import get_db_session
from abc import ABC

M = TypeVar("M")  # 模型类型
K = TypeVar("K")  # 主键类型

class BaseRepositoryAsync(Generic[M, K], ABC):
    def __init__(self, db: AsyncSession = Depends(get_db_session)):
        self.db = db
        self.model = self._resolve_model_type()  # 更可靠的模型类型解析
    
    def _resolve_model_type(self) -> Type[M]:
        """通过泛型参数解析模型类型"""
        origin = getattr(self.__class__, "__orig_bases__", [])
        if origin and hasattr(origin[0], "__args__"):
            return origin[0].__args__[0]
        raise TypeError("无法自动解析模型类型，请显式指定")

    async def list_async(
        self, 
        filters: Optional[dict] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> List[M]:
        """异步分页查询"""
        query = select(self.model)
        if filters:
            query = query.filter_by(**filters)
        result = await self.db.execute(query.offset(offset).limit(limit))
        return result.scalars().all()

    async def create_async(self, instance: M) -> M:
        """异步创建"""
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance