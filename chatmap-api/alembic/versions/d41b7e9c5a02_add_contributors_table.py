"""add contributors table

Revision ID: d41b7e9c5a02
Revises: a3f9c1d27b54
Create Date: 2026-10-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd41b7e9c5a02'
down_revision: Union[str, Sequence[str], None] = 'a3f9c1d27b54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'contributors',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('map_id', sa.String(), nullable=False),
        sa.Column('invitation_id', sa.String(), nullable=False),
        sa.Column('secret_hash', sa.String(), nullable=True),
        sa.Column('nickname', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('removed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['map_id'], ['maps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invitation_id'], ['invitations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('map_id', 'secret_hash', name='uq_contributors_map_id_secret_hash'),
    )
    op.create_index(
        'ix_contributors_invitation_id_created_at',
        'contributors',
        ['invitation_id', 'created_at'],
    )
    op.create_index('ix_contributors_secret_hash', 'contributors', ['secret_hash'])


def downgrade() -> None:
    op.drop_index('ix_contributors_secret_hash', table_name='contributors')
    op.drop_index('ix_contributors_invitation_id_created_at', table_name='contributors')
    op.drop_table('contributors')
