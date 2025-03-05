"""Actress model module."""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

@dataclass
class Actress:
    """Actress data model."""
    
    name: str
    avatar_url: Optional[str] = None
    detail_url: Optional[str] = None
    video_count: int = 0
    id: Optional[int] = None
    profile_image: Optional[str] = None
    birth_date: Optional[str] = None
    height: Optional[int] = None
    bust: Optional[int] = None
    waist: Optional[int] = None
    hips: Optional[int] = None
    blood_type: Optional[str] = None
    hometown: Optional[str] = None
    hobby: Optional[str] = None
    description: Optional[str] = None
