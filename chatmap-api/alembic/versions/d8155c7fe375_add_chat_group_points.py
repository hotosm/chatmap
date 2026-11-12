"""Add the places of chat groups

A chat group of a live map can be about one or two points of the map: its
messages most likely tell about them. chat_group_points keeps them; they go
with the group or the point.

Revision ID: d8155c7fe375
Revises: c8f3a1e6d924
Create Date: 2026-11-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd8155c7fe375'
down_revision: Union[str, Sequence[str], None] = 'c8f3a1e6d924'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'chat_group_points',
        sa.Column('group_id', sa.String(), nullable=False),
        sa.Column('point_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['chat_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('group_id', 'point_id'),
    )
    # A point that goes takes its rows with it
    op.create_index('ix_chat_group_points_point_id', 'chat_group_points', ['point_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_chat_group_points_point_id', table_name='chat_group_points')
    op.drop_table('chat_group_points')
