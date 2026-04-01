"""Add auto-updated centroids for maps

Revision ID: 74a24da4d758
Revises: c861b8a8e39f
Create Date: 2026-04-01 12:08:02.169896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '74a24da4d758'
down_revision: Union[str, Sequence[str], None] = 'c861b8a8e39f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CREATE_OR_REPLACE_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION update_map_centroid()
RETURNS TRIGGER AS $$
DECLARE
    v_map_id VARCHAR;
    v_centroid GEOMETRY;
BEGIN
    -- IF delete, use OLD
    IF TG_OP = 'DELETE' THEN
        v_map_id := OLD.map_id;
    ELSE
        -- For INSERT and UPDATE, use NEW
        v_map_id := NEW.map_id;
    END IF;

    -- If map_id is null, skip
    IF v_map_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Calculate the centroid
    WITH sampled_points AS (
        SELECT geom
        FROM points
        WHERE map_id = v_map_id 
        ORDER BY random()
        LIMIT 50
    )
    SELECT ST_Centroid(ST_Collect(geom)) INTO v_centroid
    FROM sampled_points;

    -- Update the maps table
    UPDATE "maps"
    SET centroid = v_centroid
    WHERE id = v_map_id;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

CREATE_TRIGGER_SQL = """
CREATE TRIGGER trg_points_update_centroid
AFTER INSERT OR UPDATE OR DELETE ON points
FOR EACH ROW
EXECUTE FUNCTION update_map_centroid();
"""

def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE maps ADD COLUMN IF NOT EXISTS centroid GEOMETRY(POINT, 4326);")
    # Trigger for keeping the column updated
    op.execute(CREATE_OR_REPLACE_FUNCTION_SQL)
    op.execute(CREATE_TRIGGER_SQL)
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TRIGGER IF EXISTS trg_points_update_centroid ON points;")
    op.execute("DROP FUNCTION IF EXISTS update_map_centroid();")
    op.execute("ALTER TABLE maps DROP COLUMN IF EXISTS centroid;")
    pass
