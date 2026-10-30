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
from contextlib import contextmanager
from enum import Enum
from sqlalchemy import (
    create_engine, Column, String, select, DateTime, ForeignKey, func,
    Enum as SqlEnum, Boolean, Integer, BigInteger, Identity, Interval,
    ForeignKeyConstraint, UniqueConstraint, true
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker, declarative_base, Session, relationship
from geoalchemy2 import Geometry
from settings import CHATMAP_DB, CHATMAP_DB_USER, CHATMAP_DB_PASSWORD, CHATMAP_DB_PORT, CHATMAP_DB_HOST
from datetime import datetime

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
    PUBLIC = "public"

    def __repr__(self) -> str:
        return f"<{self.value!r}>"


# Model representing a user's map
class Map(Base):
    __tablename__ = "maps"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, default="Untitled")
    description = Column(String, default="")
    sharing = Column(SqlEnum(SharePermission, name="sharing_permission"),
                     nullable=False,
                     default=SharePermission.PRIVATE)
    owner_id = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=False), default=datetime.now, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.now, nullable=False)
    is_live = Column(Boolean, default=False, nullable=False)
    bot_active = Column(Boolean, default=False, nullable=False)
    # How many days the messages of its chat groups are kept
    messages_kept_days = Column(Integer, nullable=False, default=30, server_default="30")
    centroid = Column(Geometry(geometry_type="POINT", srid=4326), nullable=True, default=None)

    # Relationship to Point model
    points = relationship(
        "Point",
        back_populates="map",
        cascade="all, delete-orphan",
    )


def get_or_create_live_map(db, user_id: str) -> str:
    """
    Retrieves the map ID for a given user, or creates a new one if it doesn't exist.

    Args:
        db (Session): SQLAlchemy database session
        user_id (str): Unique identifier for the user

    Returns:
        str: The ID of the map associated with the user
    """
    with db.begin():
        stmt = select(Map.id).where(Map.owner_id == user_id, Map.is_live)
        map_id = db.execute(stmt).scalar_one_or_none()

        if map_id:
            return map_id

        # If no map exists, create a new one
        new_map = Map(owner_id=user_id, is_live=True)
        db.add(new_map)
        db.commit()
        db.refresh(new_map)

        return new_map.id


def get_live_map_id(db, user_id: str) -> str:
    """
    Returns the id of the user's live map.

    Read-only sibling of get_or_create_live_map: the survey flow needs the same
    map id the point pipeline writes its points to, and by the time it runs that
    map is already there. Raises if there is no live map, or more than one.
    """
    return db.execute(
        select(Map.id).where(Map.owner_id == user_id, Map.is_live)
    ).scalar_one()


# Tags of points as key=value, as in OpenStreetMap: each map defines its keys
# (a status, the fuel there is, a category...). Free tags are not keys: they
# stay as text in points.tags. Rules the database keeps are in the migration
# e3a1f7c2b9d4.

# Model representing a key the points of a map can have
class MapKey(Base):
    __tablename__ = "map_keys"
    # Target of the copy of "single" in point_tags; a key is once per map
    # whatever its case (an index in the migration)
    __table_args__ = (
        UniqueConstraint("id", "single", name="map_keys_id_single_key"),
    )
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    map_id = Column(String, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    key = Column(String, nullable=False)
    # One value per point (a status) or many (the services there are)
    single = Column(Boolean, nullable=False)
    # Only its options (a status) or any text (notes)
    closed = Column(Boolean, nullable=False)
    # The key whose colors the points of the map show by default; one at most per map
    colors_map = Column(Boolean, nullable=False, default=False)
    position = Column(Integer, nullable=False, default=0)
    archived_at = Column(DateTime(timezone=True), nullable=True)


# Model representing an option of a key with a list: "Closed" for a status
class MapKeyValue(Base):
    __tablename__ = "map_key_values"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_id = Column(String, ForeignKey("map_keys.id", ondelete="CASCADE"), nullable=False)
    value = Column(String, nullable=False)
    description = Column(String, nullable=False, default="")
    color = Column(String, nullable=True)
    position = Column(Integer, nullable=False, default=0)
    # How long it lasts without being confirmed; None: it does not expire
    expires_after = Column(Interval, nullable=True)
    # An archived value cannot be given to a point; the points having it keep it
    archived_at = Column(DateTime(timezone=True), nullable=True)


# Model representing what a point has now: one row per value. It is always
# what the changes of the point say (see PointTagChange).
class PointTag(Base):
    __tablename__ = "point_tags"
    __table_args__ = (
        ForeignKeyConstraint(
            ["key_id", "single"], ["map_keys.id", "map_keys.single"], ondelete="CASCADE",
        ),
    )
    id = Column(BigInteger, Identity(), primary_key=True)
    point_id = Column(String, ForeignKey("points.id", ondelete="CASCADE"), nullable=False)
    key_id = Column(String, nullable=False)
    single = Column(Boolean, nullable=False)
    # Exactly one: a value of the list, or a free one
    value_id = Column(String, ForeignKey("map_key_values.id"), nullable=True)
    value = Column(String, nullable=True)
    # Since when it has this value, and the last time someone said so
    since = Column(DateTime(timezone=True), nullable=False)
    confirmed_at = Column(DateTime(timezone=True), nullable=False)


# Model representing a change of a tag of a point, or its confirmation. Rows
# are only added; undoing one marks it.
class PointTagChange(Base):
    __tablename__ = "point_tag_changes"
    id = Column(BigInteger, Identity(), primary_key=True)
    point_id = Column(String, ForeignKey("points.id", ondelete="CASCADE"), nullable=False)
    key_id = Column(String, ForeignKey("map_keys.id", ondelete="CASCADE"), nullable=False)
    # "set" (give or confirm a value) or "remove"
    action = Column(String, nullable=False)
    value_id = Column(String, ForeignKey("map_key_values.id", ondelete="SET NULL"), nullable=True)
    # The name the value had then
    value = Column(String, nullable=True)
    # When it happened: the time of the message, or of the click. It orders the changes.
    happened_at = Column(DateTime(timezone=True), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    # manual, message, rule, model, import, system (a point moved to another map)
    source = Column(String, nullable=False)
    message_id = Column(String, nullable=True)
    user_id = Column(String, nullable=True)
    undone_at = Column(DateTime(timezone=True), nullable=True)
    undone_by = Column(String, nullable=True)


# Model representing a chat group a live map listens to. Only groups its owner
# enabled are here: nothing is kept from the others, not even their names.
# A group disabled later stays: its messages are kept, hidden from the map,
# until they expire (or go when it is disabled, if its owner asks).
class ChatGroup(Base):
    __tablename__ = "chat_groups"
    __table_args__ = (UniqueConstraint("map_id", "chat"),)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    map_id = Column(String, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    # Pseudonym of the chat (see store.group_messages_store.pseudonym)
    chat = Column(String, nullable=False)
    name = Column(String, nullable=False, default="", server_default="")
    enabled = Column(Boolean, nullable=False, default=True, server_default=true())
    # When it was last enabled: nothing said in the group before is kept
    enabled_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


# Model representing a message of a chat group, kept so the owner of the map
# can link it to a place. Text and location only; who sent it, as a pseudonym.
class GroupMessage(Base):
    __tablename__ = "group_messages"
    # A message read twice from the stream is kept once
    __table_args__ = (UniqueConstraint("map_id", "stream_id"),)
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    map_id = Column(String, ForeignKey("maps.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(String, ForeignKey("chat_groups.id", ondelete="CASCADE"), nullable=False)
    stream_id = Column(String, nullable=False)
    sender = Column(String, nullable=False)
    text = Column(String, nullable=False, default="", server_default="")
    location = Column(String, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    dismissed_at = Column(DateTime(timezone=True), nullable=True)


# Model representing a geographic point in a map
class Point(Base):
    __tablename__ = "points"
    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    geom = Column(Geometry(geometry_type="POINT", srid=4326))  # WGS84 coordinate system
    message = Column(String)
    username = Column(String)
    time = Column(DateTime(timezone=False), default=datetime.now(), nullable=False)
    file = Column(String)
    tags = Column(String)
    removed = Column(Boolean, nullable=False, default=False)

    map_id = Column(String, ForeignKey("maps.id"), index=True, nullable=False)
    map = relationship("Map", back_populates="points")
    contributor_id = Column(String, nullable=True)


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
    map_id = get_or_create_live_map(db, user_id)
    for pt in points:
        pt.setdefault("map_id", map_id)
    # Points already in another map move to this one: the tags of the old map are not theirs
    moving = [row.id for row in db.execute(
        select(Point.id).where(Point.id.in_([pt["id"] for pt in points if pt.get("id")]), Point.map_id != map_id)
    )]
    stmt = insert(Point).values(points)
    update_dict = {
        "geom": stmt.excluded.geom,
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
    if moving:
        # Imported here: the stores import this module
        from store.point_tags_store import clear_tags_of
        clear_tags_of(db, moving)
    db.commit()


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


@contextmanager
def session_scope():
    """
    Context-managed database session for code outside FastAPI's dependency
    system (stores, the conversation listener, the CLI). Unlike get_db_session,
    the session is closed when the `with` block exits -- after the work is done,
    not before it starts.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
