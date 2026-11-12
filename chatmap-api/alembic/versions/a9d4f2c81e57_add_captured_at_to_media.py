"""add captured_at to media

Revision ID: a9d4f2c81e57
Revises: f1b8d3a67c24
Create Date: 2026-10-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a9d4f2c81e57'
down_revision: Union[str, Sequence[str], None] = 'f1b8d3a67c24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Media uploaded before this column has no known capture time, so it stays NULL
    op.add_column('media', sa.Column('captured_at', sa.DateTime(timezone=False), nullable=True))


def downgrade() -> None:
    op.drop_column('media', 'captured_at')
