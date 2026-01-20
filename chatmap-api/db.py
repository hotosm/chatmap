import uuid
import logging
from enum import Enum
from sqlalchemy import create_engine, Column, String, select, DateTime, text, ForeignKey, func, Enum as SqlEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from geoalchemy2 import Geometry
from typing import Dict, List, Literal, Tuple
from settings import CHATMAP_DB, CHATMAP_DB_USER, CHATMAP_DB_PASSWORD, CHATMAP_DB_PORT, CHATMAP_DB_HOST
from datetime import datetime
from pydantic import BaseModel

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

class SharePermission(str, Enum):
    PRIVATE = "private"
    PUBLIC  = "public"

    def __repr__(self) -> str:
        return f"<{self.value!r}>"

# Map (collection of points that belongs to a user)
class Map(Base):
    __tablename__ = "maps"
    __table_args__ = (
        UniqueConstraint("owner_id", name="uq_maps_owner_id"),
    )
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, default="Untitled")
    sharing = Column(SqlEnum(SharePermission, name="sharing_permission"),
                     nullable=False,
                     default=SharePermission.PRIVATE)
    owner_id = Column(String, nullable=False, index=True)

    points = relationship(
        "Point",
        back_populates="map",
        cascade="all, delete-orphan",
    )
    
    
# Get map id for user or create a new one if it doesn't exist
def get_or_create_map(db, user_id: str) -> str:
    # Get map
    stmt = select(Map.id).where(Map.owner_id == user_id)
    map_id = db.execute(stmt).scalar_one_or_none()
    if map_id:
        return map_id

    # If no map, create a new one
    new_map = Map(owner_id=user_id)
    db.add(new_map)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        map_id = db.execute(stmt).scalar_one()
    else:
        db.refresh(new_map)
        map_id = new_map.id

    return map_id

# Point (related to a map)
class Point(Base):
    __tablename__ = "points"
    id = Column(String, primary_key=True, index=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326))
    message = Column(String)
    username = Column(String)
    time = Column(DateTime(timezone=False), default=datetime.now(), nullable=False)
    file = Column(String)

    map_id = Column(String, ForeignKey("maps.id"), index=True, nullable=False)
    map    = relationship("Map", back_populates="points")

# Run insert queries for points, including on_conflict,
# coalescing messages and files
def add_points(db: Session, points, user_id):
    map_id = get_or_create_map(db, user_id)
    for pt in points:
        pt.setdefault("map_id", map_id)
    stmt = insert(Point).values(points)
    update_dict = {
        "geom":    stmt.excluded.geom,
        "message": func.coalesce(stmt.excluded.message, Point.message),
        "username": stmt.excluded.username,
        "file": func.coalesce(stmt.excluded.file, Point.file),
        "map_id": map_id
    }
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_=update_dict
    )
    db.execute(stmt)
    db.commit()


# GeoJson models
class FeatureGeometry(BaseModel):
    type: Literal["Point"]
    coordinates: Tuple[float, float]  # GeoJSON is [lon, lat]

class FeatureProperties(BaseModel):
    id: str
    time: datetime
    username_id: str
    message: str | None = None
    file: str | None

class Feature(BaseModel):
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: FeatureProperties

class FeatureCollection(BaseModel):
    id: str
    sharing: str
    type: Literal["FeatureCollection"]
    features: List[Feature]

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