from typing import Generator
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.services import ServiceFactory

def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting DB session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_services(db: Session = Depends(get_db)) -> ServiceFactory:
    """
    Dependency for getting services factory
    """
    return ServiceFactory(db)