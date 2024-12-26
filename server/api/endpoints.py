import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import APIRouter, Request
from pydantic import BaseModel

from core.game_loop import game_loop
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
    updated_at: datetime

@endpoints.get("/games", response_model=List[GameInfo])
async def get_games(_: Request) -> List[GameInfo]:
    active_games = []
    
    for room in game_loop.rooms.values():
        if not room.is_expired:
            active_games.append(GameInfo(
                id=uuid.UUID(room.game_id),
                state=room.game_state.state,
                player_count=len([p for p in room.players.values() if p.connected]),
                left_score=room.game_state.left_score,
                right_score=room.game_state.right_score,
                winner=room.game_state.winner,
                updated_at=room.last_activity
            ))
    
    return active_games

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