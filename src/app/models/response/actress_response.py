from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class ActressResponse(BaseModel):
    id: int
    # 其他需要的字段
    
    model_config = ConfigDict(from_attributes=True)


class ActressNameResponse(BaseModel):
    id: int
    actress_id: int
    language: str
    name: str
    
    class Config:
        from_attributes = True

class ActressResponse(BaseModel):
    id: int
    created_at: datetime
    names: List[ActressNameResponse] = []
    
    class Config:
        from_attributes = True

class ActressDetailResponse(BaseModel):
    id: int
    created_at: datetime
    names: List[ActressNameResponse] = []
    movies: List[dict] = []  # 或者使用专门的 MovieResponse 类
    
    class Config:
        from_attributes = True