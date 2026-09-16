"""Add bot_active to maps

Revision ID: 82ba73de882d
Revises: 7209ac6b2b3a
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82ba73de882d'
down_revision: Union[str, Sequence[str], None] = '7209ac6b2b3a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('maps', sa.Column('bot_active', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('maps', 'bot_active')
