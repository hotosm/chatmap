"""Tell the places of a map from the reports

A place is a point the owner of a map made on the dashboard; a point from a
location shared in a chat is a report, which the dashboard leaves out.
Messages are linked to places only. The points the maps have already are
not taken for places: only the ones the owner makes from now on are.

Revision ID: c8f3a1e6d924
Revises: c4f8a2d6e1b7
Create Date: 2026-11-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c8f3a1e6d924'
down_revision: Union[str, Sequence[str], None] = 'c4f8a2d6e1b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('points', sa.Column('place', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('points', 'place')
