"""Add bot_configured_messages table

Revision ID: c41d7f9a2e08
Revises: 82ba73de882d
Create Date: 2026-08-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c41d7f9a2e08'
down_revision: Union[str, Sequence[str], None] = '82ba73de882d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

bot_step = postgresql.ENUM(
    'start', 'media', 'location', 'single_choice', 'free_text', 'end', 'max_attempts',
    name='bot_step',
    create_type=False,
)


def upgrade() -> None:
    """Upgrade schema."""
    bot_step.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'bot_configured_messages',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('bot_step', bot_step, nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('content', sa.String(), nullable=False, server_default=''),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column('max_attempts_quantity', sa.Integer(), nullable=True),
        sa.Column('to_restart', sa.String(), nullable=True),
        sa.Column('to_cancel', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_configured_messages_id'), 'bot_configured_messages', ['id'])
    op.create_index(op.f('ix_bot_configured_messages_map_id'), 'bot_configured_messages', ['map_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_bot_configured_messages_map_id'), table_name='bot_configured_messages')
    op.drop_index(op.f('ix_bot_configured_messages_id'), table_name='bot_configured_messages')
    op.drop_table('bot_configured_messages')
    bot_step.drop(op.get_bind(), checkfirst=True)
