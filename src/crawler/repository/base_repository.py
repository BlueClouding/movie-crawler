from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Type, TypeVar
from fastapi import Depends
from sqlalchemy.orm import Session, lazyload
from app.config.database import get_db_session

M = TypeVar("M")  # 模型类型
K = TypeVar("K")  # 主键类型

class BaseRepository(Generic[M, K], ABC):
    def __init__(self, db: Session = Depends(get_db_session())):
        self.db = db
        self.model: Type[M] = self.__class__.__orig_bases__[0].__args__[0]  # 自动获取泛型类型[1](@ref)
    
    def list(self, 
        filters: Optional[dict] = None,
        limit: int = 100, 
        offset: int = 0
    ) -> List[M]:
        """通用分页查询方法"""
        query = self.db.query(self.model)
        if filters:
            query = query.filter_by(**filters)
        return query.offset(offset).limit(limit).all()
    
    def create(self, instance: M) -> M:
        """通用创建方法"""
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance

    def update(self, id: K, update_data: dict) -> M:
        """通用更新方法"""
        instance = self.db.query(self.model).get(id)
        for key, value in update_data.items():
            setattr(instance, key, value)
        self.db.commit()
        return instance

    def delete(self, id: K) -> None:
        """通用删除方法"""
        instance = self.db.query(self.model).get(id)
        self.db.delete(instance)
        self.db.commit()