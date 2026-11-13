"""create courses and progress tables

Revision ID: c1e8a93b4d21
Revises: 8422258e24bf
Create Date: 2026-09-21 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c1e8a93b4d21'
down_revision: Union[str, Sequence[str], None] = '8422258e24bf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create modules table
    op.create_table(
        'modules',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_modules_id'), 'modules', ['id'], unique=False)

    # 2. Create chapters table
    op.create_table(
        'chapters',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('module_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['module_id'], ['modules.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chapters_id'), 'chapters', ['id'], unique=False)
    op.create_index(op.f('ix_chapters_module_id'), 'chapters', ['module_id'], unique=False)

    # 3. Create topics table
    op.create_table(
        'topics',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('chapter_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False, server_default=''),
        sa.Column('content_path', sa.String(length=512), nullable=True),
        sa.Column('order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['chapter_id'], ['chapters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_topics_id'), 'topics', ['id'], unique=False)
    op.create_index(op.f('ix_topics_chapter_id'), 'topics', ['chapter_id'], unique=False)

    # 4. Create user_topic_progress table
    op.create_table(
        'user_topic_progress',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.String(length=64), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'topic_id', name='uq_user_topic_progress'),
    )
    op.create_index(op.f('ix_user_topic_progress_id'), 'user_topic_progress', ['id'], unique=False)
    op.create_index(op.f('ix_user_topic_progress_user_id'), 'user_topic_progress', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_topic_progress_topic_id'), 'user_topic_progress', ['topic_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_topic_progress_topic_id'), table_name='user_topic_progress')
    op.drop_index(op.f('ix_user_topic_progress_user_id'), table_name='user_topic_progress')
    op.drop_index(op.f('ix_user_topic_progress_id'), table_name='user_topic_progress')
    op.drop_table('user_topic_progress')

    op.drop_index(op.f('ix_topics_chapter_id'), table_name='topics')
    op.drop_index(op.f('ix_topics_id'), table_name='topics')
    op.drop_table('topics')

    op.drop_index(op.f('ix_chapters_module_id'), table_name='chapters')
    op.drop_index(op.f('ix_chapters_id'), table_name='chapters')
    op.drop_table('chapters')

    op.drop_index(op.f('ix_modules_id'), table_name='modules')
    op.drop_table('modules')
