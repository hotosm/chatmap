"""empty message

Revision ID: 5d7e8452f39a
Revises: 
Create Date: 2026-03-03 05:45:05.980519

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from datetime import datetime


# revision identifiers, used by Alembic.
revision: str = '5d7e8452f39a'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from db import SharePermission


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('maps',
        sa.Column('id', sa.VARCHAR(), nullable=False),
        sa.Column('name', sa.VARCHAR(), nullable=True, default="Untitled"),
        sa.Column('sharing', sa.Enum(SharePermission, name="sharing_permission"), nullable=False, default=SharePermission.PRIVATE),
        sa.Column('owner_id', sa.VARCHAR(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table('points',
        sa.Column('id', sa.VARCHAR()),
        sa.Column('geom', Geometry(geometry_type="POINT", srid=4326)),
        sa.Column('message', sa.VARCHAR()),
        sa.Column('username', sa.VARCHAR()),
        sa.Column('time', sa.DateTime(timezone=False), nullable=False),
        sa.Column('file', sa.VARCHAR()),
        sa.Column("map_id", sa.VARCHAR(), sa.ForeignKey("maps.id"), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_unique_constraint("uq_maps_owner_id", "maps", ["owner_id"])
    op.create_index("ix_maps_id", "maps", ["id"])
    op.create_index("ix_maps_owner_id", "maps", ["owner_id"])
    op.create_index("ix_points_id", "points", ["id"])
    op.create_index("ix_points_map_id", "points", ["map_id"])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('points')
    op.drop_table('maps')
    sa.Enum('sharing', SharePermission, name='sharing_permission').drop(op.get_bind())
