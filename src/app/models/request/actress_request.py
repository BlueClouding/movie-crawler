from typing import List, Optional
from pydantic import BaseModel


class ActressNameCreate(BaseModel):
    actress_id: Optional[int] = None
    language: str
    name: str
    
    class Config:
        from_attributes = True

class ActressCreate(BaseModel):
    names: List[ActressNameCreate] = []
    
    class Config:
        from_attributes = True

class ActressUpdate(BaseModel):
    names: Optional[List[ActressNameCreate]] = None
    
    class Config:
        from_attributes = True