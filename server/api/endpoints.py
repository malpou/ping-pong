import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database.config import get_db
from database.models import GameModel
from domain.ball import Ball
from domain.game import Game
from domain.paddle import Paddle

endpoints = APIRouter()

class GameInfo(BaseModel):
    id: uuid.UUID
    state: Game.State
    player_count: int
    left_score: int
    right_score: int
    winner: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@endpoints.get("/games", response_model=List[GameInfo])
async def get_games(request: Request, db: Session = Depends(get_db)) -> List[GameInfo]:
    """Get all current games and games finished within last 5 minutes."""
    five_minutes_ago = datetime.now(UTC) - timedelta(minutes=5)

    games = db.query(GameModel).filter(
        or_(
            GameModel.state != Game.State.GAME_OVER,
            GameModel.updated_at >= five_minutes_ago
        )
    ).order_by(GameModel.created_at.desc()).all()

    return [
        GameInfo(
            id=game.id,
            state=Game.State(game.state),
            player_count=game.total_connected,  # Use property
            left_score=game.left_score,
            right_score=game.right_score,
            winner=game.winner,
            created_at=game.created_at,
            updated_at=game.updated_at
        )
        for game in games
    ]

@endpoints.get("/specs")
def get_game_specs(_: Request) -> Dict:
    """Get the game specifications needed to set up the playing field."""
    ball = Ball()
    paddle = Paddle(0)

    return {
        "ball": {
            "radius": ball.radius,
            "initial": {
                "x": ball.x,
                "y": ball.y,
            }
        },
        "paddle": {
            "height": paddle.height,
            "width": paddle.width,
            "initial": {
                "y": paddle.y_position
            },
            "collision_bounds": {
                "left": Game.LEFT_PADDLE_X,
                "right": Game.RIGHT_PADDLE_X
            }
        },
        "game": {
            "points_to_win": Game.POINTS_TO_WIN,
            "bounds": {
                "width": Game.GAME_WIDTH,
                "height": Game.GAME_HEIGHT
            }
        }
    }

@endpoints.get("/health")
def health_check(_: Request) -> Dict:
    """Health check endpoint to verify the server is running."""
    return {
        "status": "healthy",
        "service": "pong-server"
    }