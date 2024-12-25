from datetime import datetime, UTC
import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from database.config import Base
from domain.game import Game


class GameModel(Base):
    __tablename__ = "games"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(SQLEnum(Game.State), default=Game.State.WAITING)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    winner = Column(String, nullable=True)
    left_score = Column(Integer, default=0)
    right_score = Column(Integer, default=0)

    # Game state
    ball_x = Column(Float, default=0.5)
    ball_y = Column(Float, default=0.5)
    left_paddle_y = Column(Float, default=0.5)
    right_paddle_y = Column(Float, default=0.5)

    # Relationships
    players = relationship("PlayerModel", back_populates="game")


class PlayerModel(Base):
    __tablename__ = "players"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(UUID(as_uuid=True), ForeignKey("games.id"))
    name = Column(String, nullable=False)  # Player's name
    role = Column(String)  # 'left' or 'right'
    connected = Column(Integer, default=True)
    joined_at = Column(DateTime, default=lambda: datetime.now(UTC))

    # Relationship
    game = relationship("GameModel", back_populates="players")