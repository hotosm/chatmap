"""Add the name of a place apart from the message of a point

A place kept its name in points.message, the same column a report keeps
what was said. Now a place has points.name: a report someone names becomes
a place without losing what it said, and a chat sending a point again (which
writes its message) does not undo its name.

Revision ID: b4d9e2f6a1c8
Revises: e5a7c3b9d2f1
Create Date: 2026-11-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b4d9e2f6a1c8'
down_revision: Union[str, Sequence[str], None] = 'e5a7c3b9d2f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('points', sa.Column('name', sa.String(), nullable=True))
    # The places made on the dashboard had their name as their message, and nothing else said
    op.execute("UPDATE points SET name = message, message = NULL WHERE place")


def downgrade() -> None:
    """Downgrade schema."""
    # A named report goes back to a report: its name had no place to stay
    op.execute("UPDATE points SET message = name WHERE place AND message IS NULL")
    op.execute("UPDATE points SET place = false WHERE place AND message IS DISTINCT FROM name")
    op.drop_column('points', 'name')
