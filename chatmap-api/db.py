from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./chatmap.sqlite3"  # for file-based DB

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserChatMap(Base):
    __tablename__ = "user_chatmap"
    id = Column(String, primary_key=True, index=True)
    geojson = Column(String, index=True)

Base.metadata.create_all(bind=engine)
