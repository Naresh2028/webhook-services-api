from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app import config
from sqlalchemy import create_engine
from contextlib import contextmanager

class Base(DeclarativeBase):
    pass
    
_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    config.DATABASE_URL,
    connect_args = _connect_args,
    pool_pre_ping = True
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit= False)

@contextmanager
def get_session():
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        
def init_db() -> None:
    from app import models
    
    Base.metadata.create_all(bind=engine)        