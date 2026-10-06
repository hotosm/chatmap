"""add media table

Revision ID: fbf85e992b56
Revises: c41d7f9a2e08
Create Date: 2026-10-05 14:43:29.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbf85e992b56'
down_revision: Union[str, Sequence[str], None] = 'c41d7f9a2e08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'media',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('point_id', sa.String(), nullable=False),
        sa.Column('storage_key', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        # A point has at most one media
        sa.UniqueConstraint('point_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('media')
