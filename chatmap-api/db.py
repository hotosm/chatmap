from sqlalchemy import create_engine, Column, String, select
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Dict

DATABASE_URL = "sqlite:///./data/chatmap.sqlite3"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserChatMap(Base):
    __tablename__ = "user_chatmap"
    id = Column(String, primary_key=True, index=True)
    geojson = Column(String, index=True)

class SessionData(Base):
    __tablename__ = "sessions"
    user_id = Column(String, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String)

def load_session(db: Session, user_id: str) -> Dict:
    result = db.execute(
        select(SessionData.key, SessionData.value).where(SessionData.user_id == user_id)
    ).fetchall()
    session_dict = {"user_id": user_id}
    for key, value in result:
        session_dict[key] = value
    return session_dict

def save_session(db: Session, session: Dict):
    user_id = session.get("user_id")
    if not user_id:
        return
    for key, value in session.items():
        if key == "user_id":
            continue
        obj = SessionData(user_id=user_id, key=key, value=str(value))
        db.merge(obj)
    db.commit()

def remove_session(db: Session, session: Dict):
    user_id = session.get("user_id")
    if not user_id:
        return
    db.query(SessionData).filter(SessionData.user_id == user_id).delete(
        synchronize_session=False
    )
    db.commit()

def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_db_session() -> Session:
    """
    Return a fresh Session object.  Call it wherever you need a DB connection.
    """
    return SessionLocal()