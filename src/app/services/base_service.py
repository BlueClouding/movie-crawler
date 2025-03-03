from typing import Generic, TypeVar, List, Optional, Any, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.entity.base import DBBaseModel

ModelType = TypeVar("ModelType", bound=DBBaseModel)

class BaseService(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: Type[ModelType]): # Corrected order: db, then model
        self.db = db
        self.model = model
    
    async def get(self, id: Any) -> Optional[ModelType]:
        """根据ID获取单个对象"""
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()
    
    async def get_all(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """获取多个对象"""
        result = await self.db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()
    
    async def create(self, *, obj_in: dict) -> ModelType:
        """创建新对象"""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, *, id: Any, obj_in: dict) -> Optional[ModelType]:
        """更新对象"""
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        db_obj = result.scalars().first()
        if db_obj:
            for field, value in obj_in.items():
                setattr(db_obj, field, value)
            await self.db.commit()
            await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(self, *, id: Any) -> Optional[ModelType]:
        """删除对象"""
        result = await self.db.execute(select(self.model).filter(self.model.id == id))
        db_obj = result.scalars().first()
        if db_obj:
            await self.db.delete(db_obj)
            await self.db.commit()
        return db_obj
    
    async def count(self) -> int:
        """获取对象总数"""
        from sqlalchemy import func
        result = await self.db.execute(select(func.count()).select_from(self.model))
        return result.scalar()