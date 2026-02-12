"""
This module defines the SQLAlchemy ORM models, database connection logic,
and utility functions for handling map and point data. It supports:

- Creating or retrieving user-specific maps
- Storing geographic points with associated metadata
- Handling duplicate points via upsert logic
- Generating GeoJSON representations of maps
"""

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

# Database connection string built from environment variables
DATABASE_URL = (
    f"postgresql://{CHATMAP_DB_USER}:{CHATMAP_DB_PASSWORD}"
    f"@{CHATMAP_DB_HOST}:{CHATMAP_DB_PORT}/{CHATMAP_DB}"
)

# SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool
)

# Ensure PostGIS extension is enabled
with engine.begin() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

# Base class for all SQLAlchemy models
Base = declarative_base()

# Session factory for database operations
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Enum for sharing permissions of a map
class SharePermission(str, Enum):
    PRIVATE = "private"
    PUBLIC  = "public"

    def __repr__(self) -> str:
        return f"<{self.value!r}>"

# Model representing a user's map
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

    # Relationship to Point model
    points = relationship(
        "Point",
        back_populates="map",
        cascade="all, delete-orphan",
    )

# Get or create a map for a given user
def get_or_create_map(db, user_id: str) -> str:
    """
    Retrieves the map ID for a given user, or creates a new one if it doesn't exist.

    Args:
        db (Session): SQLAlchemy database session
        user_id (str): Unique identifier for the user

    Returns:
        str: The ID of the map associated with the user
    """
    stmt = select(Map.id).where(Map.owner_id == user_id)
    map_id = db.execute(stmt).scalar_one_or_none()
    if map_id:
        return map_id

    # If no map exists, create a new one
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

# Model representing a geographic point in a map
class Point(Base):
    __tablename__ = "points"
    id = Column(String, primary_key=True, index=True)
    geom = Column(Geometry(geometry_type="POINT", srid=4326)) # WGS84 coordinate system
    message = Column(String)
    username = Column(String)
    time = Column(DateTime(timezone=False), default=datetime.now(), nullable=False)
    file = Column(String)

    map_id = Column(String, ForeignKey("maps.id"), index=True, nullable=False)
    map    = relationship("Map", back_populates="points")

# Insert or update multiple points for a user
def add_points(db: Session, points, user_id):
    """
    Adds or updates a batch of geographic points for a user's map.
    Uses PostgreSQL's ON CONFLICT DO UPDATE to handle duplicates.

    Args:
        db (Session): SQLAlchemy database session
        points (List[Dict]): List of point dictionaries with keys like 'id', 'geom', 'message', etc.
        user_id (str): ID of the user who owns the points
    """
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


# Models for GeoJSON output
class FeatureGeometry(BaseModel):
    """
    Represents the geometry of a GeoJSON feature (Point).
    """
    type: Literal["Point"]
    coordinates: Tuple[float, float]  # GeoJSON is [lon, lat]

class FeatureProperties(BaseModel):
    """
    Represents the properties of a GeoJSON feature.
    """
    id: str
    time: datetime
    username_id: str
    message: str | None = None
    file: str | None

class Feature(BaseModel):
    """
    Represents a GeoJSON feature.
    """
    type: Literal["Feature"]
    geometry: FeatureGeometry
    properties: FeatureProperties

class FeatureCollection(BaseModel):
    """
    Represents a GeoJSON FeatureCollection.
    """
    id: str
    sharing: str
    type: Literal["FeatureCollection"]
    features: List[Feature]

# Initialize database schema
def init_db():
    """
    Creates all database tables defined in the models.
    Should be called once at startup.
    """
    Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db_session():
    """
    Provides a database session for use in request handlers or background tasks.

    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()