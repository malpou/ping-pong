from dataclasses import dataclass
from dataclasses import field
from enum import Enum

import numpy as np

from domain.ball import Ball
from domain.paddle import Paddle
from logger import logger

@dataclass
class Game:
    class State(Enum):
        WAITING = "waiting"
        PLAYING = "playing"
        PAUSED = "paused"
        GAME_OVER = "game_over"

    POINTS_TO_WIN = 5  # Configurable win condition
    LEFT_PADDLE_X = 0.05  # X position for left paddle collision
    RIGHT_PADDLE_X = 0.95  # X position for right paddle collision
    GAME_WIDTH = 1.0  # Normalized game width
    GAME_HEIGHT = 1.0  # Normalized game height

    left_paddle: Paddle = field(default_factory=lambda: Paddle(Game.LEFT_PADDLE_X))
    right_paddle: Paddle = field(default_factory=lambda: Paddle(Game.RIGHT_PADDLE_X))
    ball: Ball = field(default_factory=Ball)
    left_score: int = 0
    right_score: int = 0
    winner: str | None = None
    room_id: str | None = None
    state: State = field(default=State.WAITING)
    player_count: int = 0

    def update(self) -> None:
        if self.winner or self.state != self.State.PLAYING or self.player_count < 2:
            return

        self.ball.update_position()

        # Check for scoring
        if self.ball.x <= 0:
            self.right_score += 1
            logger.info(f"Room {self.room_id}: Current score - Left: {self.left_score}, Right: {self.right_score} - RIGHT SCORED!")
            self.ball.reset()
            self._check_winner()
        elif self.ball.x >= self.GAME_WIDTH:
            self.left_score += 1
            logger.info(f"Room {self.room_id}: Current score - Left: {self.left_score}, Right: {self.right_score} - LEFT SCORED!")
            self.ball.reset()
            self._check_winner()

        # Basic paddle collision
        if self.left_paddle.is_on_paddle(self.ball):
            self.ball.x = self.left_paddle.x_position
            self.ball.angle += 3 * np.pi / 4

        if self.right_paddle.is_on_paddle(self.ball):
            self.ball.x = self.right_paddle.x_position
            self.ball.angle += 3 * np.pi / 4


    def add_player(self) -> None:
        self.player_count += 1
        if self.player_count == 2:
            self.state = self.State.PLAYING

    def remove_player(self) -> None:
        self.player_count -= 1
        if self.player_count < 2 and self.state == self.State.PLAYING:
            self.state = self.State.PAUSED

    def _check_winner(self) -> None:
        if self.left_score >= self.POINTS_TO_WIN:
            self.winner = "left"
            self.state = self.State.GAME_OVER
        elif self.right_score >= self.POINTS_TO_WIN:
            self.winner = "right"
            self.state = self.State.GAME_OVER