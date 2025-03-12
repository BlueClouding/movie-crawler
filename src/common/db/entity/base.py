from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.ext.declarative import declared_attr

from app.config.database import Base

class DBBaseModel(Base):
    """所有模型的基类"""
    __abstract__ = True
    
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower() + 's'
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.current_timestamp())

registry = DBBaseModel.registry._class_registry

# 转换为普通字典（注意：弱引用可能已失效）
registry_dict = dict(registry)

# 过滤内部键（如 '_sa_module'）
filtered_classes = {
    key: cls 
    for key, cls in registry_dict.items()
    if not key.startswith('_sa_') and isinstance(cls, type)
}

# 打印结果
print("Registered classes:")
for class_name, cls in filtered_classes.items():
    print(f"- {class_name}: {cls}")