"""Add what the messages of the groups suggest

The rules of a map over the messages of its groups (message_rules); the
words that say each value of a key in the chats (map_key_values.words) and
the other names of each place (place_names), to read the lines of a message;
and what a message suggests from them (message_suggestions), pending until a
person answers. What the rules do to a message stays with it: the texts to
highlight, and whether a rule hid it.

Revision ID: e5a7c3b9d2f1
Revises: d8155c7fe375
Create Date: 2026-11-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e5a7c3b9d2f1'
down_revision: Union[str, Sequence[str], None] = 'd8155c7fe375'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'message_rules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_message_rules_map_id', 'message_rules', ['map_id'])

    op.add_column('group_messages', sa.Column('dismissed_by_rule', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('group_messages', sa.Column('highlights', postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.add_column(
        'map_key_values',
        sa.Column('words', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )

    op.create_table(
        'place_names',
        sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column('point_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('point_id', 'name'),
    )
    op.create_index('ix_place_names_point_id', 'place_names', ['point_id'])

    op.create_table(
        'message_suggestions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=False),
        # The line that says it, from 0; none for the whole message, as a rule reads it
        sa.Column('line', sa.Integer(), nullable=True),
        sa.Column('point_id', sa.String(), nullable=True),
        sa.Column('key_id', sa.String(), nullable=True),
        sa.Column('value_id', sa.String(), nullable=True),
        sa.Column('rule_id', sa.String(), nullable=True),
        sa.Column('rule', sa.String(), nullable=True),
        sa.Column('words', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('doubt', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=False, server_default='pending'),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['message_id'], ['group_messages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['key_id'], ['map_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['value_id'], ['map_key_values.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['message_rules.id'], name='fk_message_suggestions_rule_id', ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    # A message, point, key or value that goes takes its suggestions with it
    for column in ('message_id', 'point_id', 'key_id', 'value_id'):
        op.create_index(f'ix_message_suggestions_{column}', 'message_suggestions', [column])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('message_suggestions')
    op.drop_index('ix_place_names_point_id', table_name='place_names')
    op.drop_table('place_names')
    op.drop_column('map_key_values', 'words')
    op.drop_column('group_messages', 'highlights')
    op.drop_column('group_messages', 'dismissed_by_rule')
    op.drop_index('ix_message_rules_map_id', table_name='message_rules')
    op.drop_table('message_rules')
