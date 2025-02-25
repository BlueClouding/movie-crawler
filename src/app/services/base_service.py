from sqlalchemy.orm import Session
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict, Union

T = TypeVar('T')

class BaseService(Generic[T]):
    def __init__(self, db: Session, model: Type[T]):
        self.db = db
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[T]:
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, obj_in: Dict[str, Any]) -> T:
        obj = self.model(**obj_in)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[T]:
        obj = self.get_by_id(id)
        if not obj:
            return None
        
        for key, value in obj_in.items():
            setattr(obj, key, value)
        
        self.db.commit()
        self.db.refresh(obj)
        return obj
    
    def delete(self, id: int) -> bool:
        obj = self.get_by_id(id)
        if not obj:
            return False
        
        self.db.delete(obj)
        self.db.commit()
        return True