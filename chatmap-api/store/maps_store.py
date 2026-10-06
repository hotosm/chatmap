import logging

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from db import session_scope, Map, Point, SharePermission
from results.error import StoreUnavailable

logger = logging.getLogger(__name__)


class MapsStore:

    @classmethod
    async def read_map(cls, map_id: str, user_id: str | None) -> tuple[Map, bool, list] | None:
        with session_scope() as db:
            try:
                map_obj = db.get(Map, map_id)

                if map_obj is None:
                    return None

                owner = map_obj.owner_id == user_id

                if map_obj.sharing != SharePermission.PUBLIC and not owner:
                    return None

                query = select(
                    Point.id,
                    Point.message,
                    func.ST_Y(Point.geom).label("lat"),
                    func.ST_X(Point.geom).label("lon"),
                    Point.time,
                    Point.file,
                    Point.removed,
                    Point.tags,
                    Point.status_id,
                    Point.status_updated_at,
                ).where(Point.map_id == map_id)

                # Removed points are only shown to the owner of the map
                if not owner:
                    query = query.where(Point.removed == False)

                return map_obj, owner, db.execute(query).all()
            except SQLAlchemyError as error:
                logger.error(f"Fetch map '{map_id}' failed with: '{error}'")
                raise StoreUnavailable
