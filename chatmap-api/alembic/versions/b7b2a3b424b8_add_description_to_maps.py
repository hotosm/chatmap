"""Add description to maps

Revision ID: b7b2a3b424b8
Revises: 74a24da4d758
Create Date: 2026-04-24 11:19:26.758597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7b2a3b424b8'
down_revision: Union[str, Sequence[str], None] = '74a24da4d758'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('maps', sa.Column('description', sa.String(), nullable=True))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('maps', 'description')
    pass
