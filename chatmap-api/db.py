from sqlalchemy import create_engine, Column, String, select, DateTime, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from geoalchemy2 import Geometry
from typing import Dict, List, Literal, Tuple
from settings import CHATMAP_DB, CHATMAP_DB_USER, CHATMAP_DB_PASSWORD, CHATMAP_DB_PORT, CHATMAP_DB_HOST
from datetime import datetime
from pydantic import BaseModel
import logging

# Logs
logger = logging.getLogger(__name__)

DATABASE_URL = (
    f"postgresql://{CHATMAP_DB_USER}:{CHATMAP_DB_PASSWORD}"
    f"@{CHATMAP_DB_HOST}:{CHATMAP_DB_PORT}/{CHATMAP_DB}"
)

engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool
)

with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

Base = declarative_base()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ChatMap Points
class Point(Base):
    __tablename__ = "points"
    id = Column(String, primary_key=True, index=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326))
    message = Column(String)
    user = Column(String)
    username = Column(String)
    time = Column(DateTime(timezone=False), default=datetime.now(), nullable=False)
    file = Column(String)
    
def add_points(db: Session, points):
    stmt = insert(Point).values(points)
    update_dict = {
        "geom":    stmt.excluded.geom,
        "message": stmt.excluded.message,
        "user": stmt.excluded.user,
        "username": stmt.excluded.username,
        "file": stmt.coalesce(stmt.excluded.file, Point.file),
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_=update_dict
    )
    db.execute(stmt)
    db.commit()

class PointOut(BaseModel):
    id: str
    coordinates: List[float]
    message: str | None = None
    username: str | None = None
    time: datetime
    file: str | None = None

    class Config:
        from_attributes = True

class FeatureGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Tuple[float, float]  # GeoJSON is [lon, lat]

class FeatureProperties(BaseModel):
    id: str
    time: datetime
    username: str
    message: str | None = None
    file: str | None

class Feature(BaseModel):
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: FeatureProperties

class FeatureCollection(BaseModel):
    _chatmapId: str
    type: Literal["FeatureCollection"]
    features: List[Feature]

# User Session Data
class SessionData(Base):
    __tablename__ = "sessions"
    user_id = Column(String, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String)

# Load user session
def load_session(db: Session, user_id: str) -> Dict:
    result = db.execute(
        select(SessionData.key, SessionData.value).where(SessionData.user_id == user_id)
    ).fetchall()
    session_dict = {"user_id": user_id}
    for key, value in result:
        session_dict[key] = value
    return session_dict

# Save user session
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

# Remove user session
def remove_session(db: Session, session: Dict):
    user_id = session.get("user_id")
    if not user_id:
        return
    db.query(SessionData).filter(SessionData.user_id == user_id).delete(
        synchronize_session=False
    )
    db.commit()

# Initialize database
def init_db():
    Base.metadata.create_all(bind=engine)

# Dependency to get DB session

def get_db_session():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()