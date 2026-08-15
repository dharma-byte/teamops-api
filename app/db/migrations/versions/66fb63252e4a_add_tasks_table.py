"""add tasks table

Revision ID: 66fb63252e4a
Revises: 8777770755c7
Create Date: 2026-08-15 20:45:32.960998

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '66fb63252e4a'
down_revision: str | Sequence[str] | None = '8777770755c7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'tasks',
        sa.Column('project_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column(
            'status',
            sa.Enum('backlog', 'todo', 'in_progress', 'in_review', 'done', name='task_status'),
            nullable=False,
        ),
        sa.Column(
            'priority',
            sa.Enum('low', 'medium', 'high', 'urgent', name='task_priority'),
            nullable=False,
        ),
        sa.Column('assignee_id', sa.UUID(), nullable=True),
        sa.Column('reporter_id', sa.UUID(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column(
            'id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_tasks_assignee_id_due_date', 'tasks', ['assignee_id', 'due_date'], unique=False
    )
    op.create_index(
        'ix_tasks_project_id_status', 'tasks', ['project_id', 'status'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_tasks_project_id_status', table_name='tasks')
    op.drop_index('ix_tasks_assignee_id_due_date', table_name='tasks')
    op.drop_table('tasks')
