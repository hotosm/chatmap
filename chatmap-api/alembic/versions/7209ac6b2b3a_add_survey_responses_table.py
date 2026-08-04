"""add survey_responses table

Revision ID: 7209ac6b2b3a
Revises: b7b2a3b424b8
Create Date: 2026-08-03 20:42:01.152034

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7209ac6b2b3a'
down_revision: Union[str, Sequence[str], None] = 'b7b2a3b424b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'survey_responses',
        sa.Column('point_id', sa.String(), nullable=False),
        sa.Column('answers', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('point_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('survey_responses')
