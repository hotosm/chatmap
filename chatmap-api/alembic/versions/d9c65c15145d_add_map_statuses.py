"""Add map statuses and point status

Revision ID: d9c65c15145d
Revises: fbf85e992b56
Create Date: 2026-10-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd9c65c15145d'
down_revision: Union[str, Sequence[str], None] = 'fbf85e992b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'map_statuses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False, server_default=''),
        sa.Column('color', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_map_statuses_id'), 'map_statuses', ['id'])
    op.create_index(op.f('ix_map_statuses_map_id'), 'map_statuses', ['map_id'])

    op.add_column('points', sa.Column('status_id', sa.String(), nullable=True))
    op.add_column('points', sa.Column('status_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f('points_status_id_fkey'), 'points', 'map_statuses', ['status_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(op.f('ix_points_status_id'), 'points', ['status_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_points_status_id'), table_name='points')
    op.drop_constraint(op.f('points_status_id_fkey'), 'points', type_='foreignkey')
    op.drop_column('points', 'status_updated_at')
    op.drop_column('points', 'status_id')
    op.drop_index(op.f('ix_map_statuses_map_id'), table_name='map_statuses')
    op.drop_index(op.f('ix_map_statuses_id'), table_name='map_statuses')
    op.drop_table('map_statuses')
