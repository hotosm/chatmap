"""Link the changes of tags to the group messages they come from

A change of a tag with source "message" keeps the id of its message. When the
message goes (it expired, or its group was removed with its messages) the
change stays in the history of the point, without it.

Revision ID: c4f8a2d6e1b7
Revises: b7d2e4a91c3f
Create Date: 2026-10-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c4f8a2d6e1b7'
down_revision: Union[str, Sequence[str], None] = 'b7d2e4a91c3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No change came from a message before: any id there is of none
    op.execute(
        "UPDATE point_tag_changes SET message_id = NULL WHERE message_id IS NOT NULL "
        "AND message_id NOT IN (SELECT id FROM group_messages)"
    )
    op.create_foreign_key(
        'fk_point_tag_changes_message_id', 'point_tag_changes', 'group_messages',
        ['message_id'], ['id'], ondelete='SET NULL',
    )
    # The links of a page of messages
    op.create_index('ix_point_tag_changes_message_id', 'point_tag_changes', ['message_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_point_tag_changes_message_id', table_name='point_tag_changes')
    op.drop_constraint('fk_point_tag_changes_message_id', 'point_tag_changes', type_='foreignkey')
