from dataclasses import dataclass
from dataclasses import field
from scipy import interpolate
import time

import numpy as np

from domain.ball import Ball
from domain.enums import GameState, GameSide
from domain.paddle import Paddle
from logger import logger

@dataclass
class Game:
    POINTS_TO_WIN = 5  # Configurable win condition
    LEFT_PADDLE_X = 0.05  # X position for left paddle collision
    RIGHT_PADDLE_X = 0.95  # X position for right paddle collision
    GAME_WIDTH = 1.0  # Normalized game width
    GAME_HEIGHT = 1.0  # Normalized game height
    SCORE_DELAY = 1.0  # 1 second delay after scoring
    START_DELAY = 3.0  # 3 second delay at game start

    # Speed multiplier constants
    BASE_SPEED = 1/60 * 1/2
    SPEED_TIER_1 = 1.25  # After 5 hits
    SPEED_TIER_2 = 1.5  # After 10 hits
    SPEED_INCREMENT = 0.1  # Per hit after 10 hits
    MAX_SPEED_MULTIPLIER = 3.0  # After 20 hits

    left_paddle: Paddle = field(default_factory=lambda: Paddle(Game.LEFT_PADDLE_X))
    right_paddle: Paddle = field(default_factory=lambda: Paddle(Game.RIGHT_PADDLE_X))
    ball: Ball = field(default_factory=Ball)
    left_score: int = 0
    right_score: int = 0
    winner: str | None = None
    room_id: str | None = None
    state: GameState = field(default=GameState.WAITING)
    player_count: int = 0
    ball_towards: GameSide = GameSide.LEFT
    score_timer: float = 0
    start_timer: float = 0
    scoring_side: GameSide | None = None
    paddle_hits: int = 0
    starting_state: bool = False

    def update(self) -> None:
        if self.winner or self.state != GameState.PLAYING or self.player_count < 2:
            return

        # Handle start delay
        if self.starting_state:
            if time.time() - self.start_timer >= self.START_DELAY:
                self.starting_state = False
                self.ball.reset(GameSide.LEFT)
            return

        # Handle scoring delay
        if self.scoring_side is not None:
            if time.time() - self.score_timer >= self.SCORE_DELAY:
                self.ball.reset(self.scoring_side)
                self.scoring_side = None
            return

        self.ball.update_position()

        # Check for scoring
        if self.ball.x <= 0:
            self.handle_scoring(GameSide.LEFT, self.right_score + 1)
        elif self.ball.x >= self.GAME_WIDTH:
            self.handle_scoring(GameSide.RIGHT, self.left_score + 1)

        # Find which direction the ball is going towards
        self.ball_towards = self.determine_ball_towards()

        # Basic paddle collision
        if (
            (self.left_paddle.is_on_paddle(self.ball)) and 
            self.ball_towards == GameSide.LEFT
        ):
            self.handle_paddle_hit(self.left_paddle)

        if (
            (self.right_paddle.is_on_paddle(self.ball)) and 
            self.ball_towards == GameSide.RIGHT
        ):
            self.handle_paddle_hit(self.right_paddle)

    def determine_ball_towards(self) -> GameSide :
        if (np.pi / 2 <= self.ball.angle <= 3 * np.pi / 2):
            return GameSide.LEFT
        if (
            (self.ball.angle <= (np.pi / 2)) or 
            (self.ball.angle >= (3 * np.pi / 2))
        ):
            return GameSide.RIGHT

    def calc_angle(self, paddle: Paddle) -> float:
        if self.ball_towards == GameSide.LEFT:
            angle_min = -np.pi / 3
            angle_max = np.pi / 3
        else:
            angle_min = 4 * np.pi / 3
            angle_max = 2 * np.pi / 3

        y_values = [paddle.y_min, paddle.y_max]
        angle_values = [angle_min, angle_max]

        # Scipy interpolation function 
        f = interpolate.interp1d(y_values, angle_values)

        angle_interpolated = f(self.ball.y)
        # normalize the angle to [0, 2*pi]
        angle_interpolated = self.ball.normalize_angle(angle_interpolated)

        return angle_interpolated

    def add_player(self) -> None:
        self.player_count += 1
        if self.player_count == 2:
            self.state = GameState.PLAYING
            self.starting_state = True
            self.start_timer = time.time()

    def remove_player(self) -> None:
        self.player_count -= 1
        if self.player_count < 2 and self.state == GameState.PLAYING:
            self.state = GameState.PAUSED

    def _check_winner(self) -> None:
        if self.left_score >= self.POINTS_TO_WIN:
            self.winner = "left"
            self.state = GameState.GAME_OVER
        elif self.right_score >= self.POINTS_TO_WIN:
            self.winner = "right"
            self.state = GameState.GAME_OVER

    def reset_paddles(self) -> None:
        """Reset paddles to center position"""
        self.left_paddle.reset_position()
        self.right_paddle.reset_position()

    def handle_scoring(self, side: GameSide, new_score: int) -> None:
        if side == GameSide.LEFT:
            self.right_score = new_score
            logger.info(f"Room {self.room_id}: Current score - Left: {self.left_score}, Right: {self.right_score} - RIGHT SCORED!")
        else:
            self.left_score = new_score
            logger.info(f"Room {self.room_id}: Current score - Left: {self.left_score}, Right: {self.right_score} - LEFT SCORED!")
        
        self.paddle_hits = 0
        self.ball.set_speed(self.BASE_SPEED)
        self.reset_paddles()
        self.score_timer = time.time()
        self.scoring_side = side
        self._check_winner()

    def calculate_ball_speed(self) -> float:
        if self.paddle_hits < 5:
            return self.BASE_SPEED
        elif self.paddle_hits < 10:
            return self.BASE_SPEED * self.SPEED_TIER_1
        elif self.paddle_hits < 20:
            multiplier = self.SPEED_TIER_2 + (self.paddle_hits - 10) * self.SPEED_INCREMENT
            return self.BASE_SPEED * min(multiplier, self.MAX_SPEED_MULTIPLIER)
        else:
            return self.BASE_SPEED * self.MAX_SPEED_MULTIPLIER

    def handle_paddle_hit(self, paddle: Paddle) -> None:
        self.paddle_hits += 1
        self.ball.set_speed(self.calculate_ball_speed())
        self.ball.angle = self.calc_angle(paddle)