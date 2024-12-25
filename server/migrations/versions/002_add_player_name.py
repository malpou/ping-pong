"""add player name

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add name column to players table
    op.add_column('players',
        sa.Column('name', sa.String(), nullable=False, server_default='Anonymous')
    )


def downgrade() -> None:
    # Remove name column from players table
    op.drop_column('players', 'name') 