from typing import Generic, TypeVar, Type, List, Optional, Any, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.future import select
from fastapi.encoders import jsonable_encoder

from app.db.entity.base import DBBaseModel


ModelType = TypeVar("ModelType", bound=DBBaseModel)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """根据ID获取单个对象"""
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()
    
    async def get_multi(
        self, db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[ModelType]:
        """获取多个对象"""
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return result.scalars().all()
    
    async def create(self, db: AsyncSession, *, obj_in: Dict[str, Any]) -> ModelType:
        """创建新对象"""
        obj_data = obj_in
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self, db: AsyncSession, *, db_obj: ModelType, obj_in: Union[Dict[str, Any], ModelType]
    ) -> ModelType:
        """更新对象"""
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = jsonable_encoder(obj_in)
        
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def remove(self, db: AsyncSession, *, id: int) -> ModelType:
        """删除对象"""
        result = await db.execute(select(self.model).filter(self.model.id == id))
        obj = result.scalars().first()
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
    
    async def count(self, db: AsyncSession) -> int:
        """获取对象总数"""
        result = await db.execute(select(func.count()).select_from(self.model))
        return result.scalar()