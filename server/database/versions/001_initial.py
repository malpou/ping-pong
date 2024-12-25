"""initial with uuids

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from domain.game import Game

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create games table
    op.create_table('games',
                    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
                    sa.Column('state', sa.Enum(Game.State), nullable=False),
                    sa.Column('created_at', sa.DateTime(), nullable=False),
                    sa.Column('updated_at', sa.DateTime(), nullable=False),
                    sa.Column('winner', sa.String(), nullable=True),
                    sa.Column('left_score', sa.Integer(), nullable=False),
                    sa.Column('right_score', sa.Integer(), nullable=False),
                    sa.Column('ball_x', sa.Float(), nullable=False),
                    sa.Column('ball_y', sa.Float(), nullable=False),
                    sa.Column('left_paddle_y', sa.Float(), nullable=False),
                    sa.Column('right_paddle_y', sa.Float(), nullable=False),
                    sa.PrimaryKeyConstraint('id')
                    )

    # Create players table
    op.create_table('players',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('game_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('connected', sa.Boolean(), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['game_id'], ['games.id']),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('players')
    op.drop_table('games')