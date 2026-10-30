"""Add chat groups and their messages

A live map listens to the chat groups its owner enables: chat_groups keeps
those groups and group_messages their messages (text and location), for as
many days as maps.messages_kept_days says.

Revision ID: b7d2e4a91c3f
Revises: a9d4f2c81e57
Create Date: 2026-10-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d2e4a91c3f'
down_revision: Union[str, Sequence[str], None] = 'a9d4f2c81e57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('maps', sa.Column('messages_kept_days', sa.Integer(), nullable=False, server_default='30'))

    op.create_table(
        'chat_groups',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('chat', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False, server_default=''),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('enabled_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('map_id', 'chat'),
    )

    op.create_table(
        'group_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('group_id', sa.String(), nullable=False),
        sa.Column('stream_id', sa.String(), nullable=False),
        sa.Column('sender', sa.String(), nullable=False),
        sa.Column('text', sa.String(), nullable=False, server_default=''),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['chat_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('map_id', 'stream_id'),
    )
    # The messages of a map, newest first, a page at a time
    op.create_index(
        'ix_group_messages_map_id_sent_at', 'group_messages', ['map_id', sa.text('sent_at DESC'), sa.text('id DESC')],
    )
    op.create_index('ix_group_messages_group_id', 'group_messages', ['group_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_group_messages_group_id', table_name='group_messages')
    op.drop_index('ix_group_messages_map_id_sent_at', table_name='group_messages')
    op.drop_table('group_messages')
    op.drop_table('chat_groups')
    op.drop_column('maps', 'messages_kept_days')
