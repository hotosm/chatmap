"""Add map keys, point tags and their changes

The status of a point becomes one more key=value tag, as in OpenStreetMap.
Each map defines its keys (status, tag, category...) and the options of the
ones with a list. What a point has now lives in point_tags; everything that
happened, in order, in point_tag_changes, and point_tags is always what those
changes say.

It replaces the statuses of d9c65c15145d: its table map_statuses and the
columns status_id and status_updated_at of points are removed. No map used
statuses yet, so there is nothing to copy. Free tags stay as text in
points.tags.

Revision ID: e3a1f7c2b9d4
Revises: d9c65c15145d
Create Date: 2026-10-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e3a1f7c2b9d4'
down_revision: Union[str, Sequence[str], None] = 'd9c65c15145d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'map_keys',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        # One value per point (status, category) or many (tags)
        sa.Column('single', sa.Boolean(), nullable=False),
        # Only values of its list (status) or any text (tags)
        sa.Column('closed', sa.Boolean(), nullable=False),
        # Keys of the system cannot be removed or renamed
        sa.Column('builtin', sa.Boolean(), nullable=False, server_default=sa.false()),
        # The key whose colors the points of the map show by default
        sa.Column('colors_map', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        # Target of the copy of "single" in point_tags
        sa.UniqueConstraint('id', 'single', name='map_keys_id_single_key'),
    )
    op.create_index(op.f('ix_map_keys_map_id'), 'map_keys', ['map_id'])
    # A key once per map, whatever its case
    op.create_index('ix_map_keys_map_id_key', 'map_keys', ['map_id', sa.text('lower(key)')], unique=True)
    # One key at most colors a map by default
    op.create_index(
        'ix_map_keys_colors_map', 'map_keys', ['map_id'], unique=True, postgresql_where=sa.text('colors_map'),
    )

    op.create_table(
        'map_key_values',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('key_id', sa.String(), nullable=False),
        sa.Column('value', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False, server_default=''),
        sa.Column('color', sa.String(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, server_default='0'),
        # How long a value lasts without being confirmed; null: it does not expire
        sa.Column('expires_after', sa.Interval(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['key_id'], ['map_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_map_key_values_key_id'), 'map_key_values', ['key_id'])
    # A name once per key, whatever its case, archived ones included
    op.create_index(
        'ix_map_key_values_key_id_value', 'map_key_values', ['key_id', sa.text('lower(value)')], unique=True,
    )

    op.create_table(
        'point_tags',
        sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column('point_id', sa.String(), nullable=False),
        sa.Column('key_id', sa.String(), nullable=False),
        sa.Column('single', sa.Boolean(), nullable=False),
        sa.Column('value_id', sa.String(), nullable=True),
        sa.Column('value', sa.String(), nullable=True),
        sa.Column('since', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        # The copy of "single" has to be the one of the key
        sa.ForeignKeyConstraint(
            ['key_id', 'single'], ['map_keys.id', 'map_keys.single'], onupdate='CASCADE', ondelete='CASCADE',
        ),
        # A value some point has cannot be removed ("in use")
        sa.ForeignKeyConstraint(['value_id'], ['map_key_values.id']),
        # Exactly one: a value of the list or a free one
        sa.CheckConstraint('(value_id IS NULL) <> (value IS NULL)', name='point_tags_one_value'),
        sa.PrimaryKeyConstraint('id'),
    )
    # One value for the keys that take one (a single status per point)
    op.create_index(
        'ix_point_tags_single', 'point_tags', ['point_id', 'key_id'], unique=True,
        postgresql_where=sa.text('single'),
    )
    # No repeated values for the keys that take many
    op.create_index(
        'ix_point_tags_value_id', 'point_tags', ['point_id', 'key_id', 'value_id'], unique=True,
        postgresql_where=sa.text('value_id IS NOT NULL'),
    )
    op.create_index(
        'ix_point_tags_value', 'point_tags', ['point_id', 'key_id', 'value'], unique=True,
        postgresql_where=sa.text('value IS NOT NULL'),
    )
    op.create_index(op.f('ix_point_tags_key_id'), 'point_tags', ['key_id'])
    op.create_index(op.f('ix_point_tags_value_id_fk'), 'point_tags', ['value_id'])

    op.create_table(
        'point_tag_changes',
        sa.Column('id', sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column('point_id', sa.String(), nullable=False),
        sa.Column('key_id', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('value_id', sa.String(), nullable=True),
        # The name the value had then: renaming it later does not change history
        sa.Column('value', sa.String(), nullable=True),
        # When it happened (the time of the message, or of the click) orders the changes
        sa.Column('happened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('message_id', sa.String(), nullable=True),
        sa.Column('user_id', sa.String(), nullable=True),
        # Undoing marks a change, it never removes it
        sa.Column('undone_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('undone_by', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['point_id'], ['points.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['key_id'], ['map_keys.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['value_id'], ['map_key_values.id'], ondelete='SET NULL'),
        sa.CheckConstraint("action IN ('set', 'remove')", name='point_tag_changes_action'),
        sa.PrimaryKeyConstraint('id'),
    )
    # The last changes of a point that count, to work out what it has now
    op.create_index(
        'ix_point_tag_changes_current', 'point_tag_changes',
        ['point_id', 'key_id', sa.text('happened_at DESC')],
        postgresql_where=sa.text('undone_at IS NULL'),
    )
    # Removing changes by how long they are kept
    op.create_index(op.f('ix_point_tag_changes_recorded_at'), 'point_tag_changes', ['recorded_at'])

    # The statuses of d9c65c15145d are kept in the tables above now
    op.drop_index(op.f('ix_points_status_id'), table_name='points')
    op.drop_constraint(op.f('points_status_id_fkey'), 'points', type_='foreignkey')
    op.drop_column('points', 'status_updated_at')
    op.drop_column('points', 'status_id')
    op.drop_index(op.f('ix_map_statuses_map_id'), table_name='map_statuses')
    op.drop_index(op.f('ix_map_statuses_id'), table_name='map_statuses')
    op.drop_table('map_statuses')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'map_statuses',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False, server_default=''),
        sa.Column('color', sa.String(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_map_statuses_id'), 'map_statuses', ['id'])
    op.create_index(op.f('ix_map_statuses_map_id'), 'map_statuses', ['map_id'])
    op.add_column('points', sa.Column('status_id', sa.String(), nullable=True))
    op.add_column('points', sa.Column('status_updated_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        op.f('points_status_id_fkey'), 'points', 'map_statuses', ['status_id'], ['id'], ondelete='SET NULL',
    )
    op.create_index(op.f('ix_points_status_id'), 'points', ['status_id'])

    op.drop_table('point_tag_changes')
    op.drop_table('point_tags')
    op.drop_table('map_key_values')
    op.drop_table('map_keys')
