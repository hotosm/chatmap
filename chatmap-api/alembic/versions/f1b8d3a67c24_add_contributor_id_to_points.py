"""add contributor_id to points

Revision ID: f1b8d3a67c24
Revises: d41b7e9c5a02
Create Date: 2026-10-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f1b8d3a67c24'
down_revision: Union[str, Sequence[str], None] = 'd41b7e9c5a02'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('points', sa.Column('contributor_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_points_contributor_id_contributors',
        'points',
        'contributors',
        ['contributor_id'],
        ['id'],
    )
    op.create_index(
        'ix_points_contributor_id_time_id',
        'points',
        ['contributor_id', 'time', 'id'],
        postgresql_where=sa.text('contributor_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_points_contributor_id_time_id', table_name='points')
    op.drop_constraint('fk_points_contributor_id_contributors', 'points', type_='foreignkey')
    op.drop_column('points', 'contributor_id')
