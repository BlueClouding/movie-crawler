
from dataclasses import dataclass
from typing import Optional

@dataclass
class GenreInfo:
    """Genre information model."""
    
    name: str
    url: str
    id: Optional[int] = None
    code: Optional[str] = None
    original_name: Optional[str] = None 
