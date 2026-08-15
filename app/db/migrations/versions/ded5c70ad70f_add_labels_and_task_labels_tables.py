"""add labels and task_labels tables

Revision ID: ded5c70ad70f
Revises: 66fb63252e4a
Create Date: 2026-08-15 20:57:10.629478

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ded5c70ad70f'
down_revision: str | Sequence[str] | None = '66fb63252e4a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'labels',
        sa.Column('org_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('color', sa.String(length=7), nullable=False),
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
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'name', name='uq_labels_org_name'),
    )
    op.create_index(op.f('ix_labels_org_id'), 'labels', ['org_id'], unique=False)
    op.create_table(
        'task_labels',
        sa.Column('task_id', sa.UUID(), nullable=False),
        sa.Column('label_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['label_id'], ['labels.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'label_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('task_labels')
    op.drop_index(op.f('ix_labels_org_id'), table_name='labels')
    op.drop_table('labels')
