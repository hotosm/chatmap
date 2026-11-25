"""Add the keyword step to the bot_step enum

Revision ID: f6a2b1c9d8e4
Revises: e5a7c3b9d2f1
Create Date: 2026-11-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f6a2b1c9d8e4'
down_revision: Union[str, Sequence[str], None] = 'e5a7c3b9d2f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE bot_step ADD VALUE IF NOT EXISTS 'keyword'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
