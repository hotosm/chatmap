"""Add removed column to Point

Revision ID: c861b8a8e39f
Revises: 51adeb808f08
Create Date: 2026-03-27 18:12:18.242978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c861b8a8e39f'
down_revision: Union[str, Sequence[str], None] = '51adeb808f08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('points', sa.Column('removed', sa.Boolean, nullable=False, default=False))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('points', 'removed')
    pass
