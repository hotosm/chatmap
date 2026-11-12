from sqlalchemy import select

from db import Map


def owner_of(db, map_id: str) -> str | None:
    return db.execute(select(Map.owner_id).where(Map.id == map_id)).scalar_one_or_none()


def owned_maps(db, user_id: str):
    query = (
        select(Map.id, Map.name)
        .where(Map.owner_id == user_id)
        .order_by(Map.created_at, Map.id)
    )

    return db.execute(query).all()
