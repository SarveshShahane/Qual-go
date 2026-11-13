"""add question_type to topics

Revision ID: d2f4e91a0b32
Revises: c1e8a93b4d21
Create Date: 2026-09-26 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd2f4e91a0b32'
down_revision: Union[str, Sequence[str], None] = 'c1e8a93b4d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'topics',
        sa.Column('question_type', sa.String(length=50), nullable=True, server_default='code')
    )


def downgrade() -> None:
    op.drop_column('topics', 'question_type')
