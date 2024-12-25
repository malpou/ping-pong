from dataclasses import dataclass
import numpy as np
from domain.ball import Ball


@dataclass
class Paddle:
    x_position: float
    y_position: float = 0.5  # Position as percentage of screen height (0-1)
    height: float = 0.2  # Height as percentage of screen height
    speed: float = 0.02  # Movement speed per frame

    def __init__(self, x_pos: float):
        self.x_position = x_pos

    def is_on_paddle(self, ball: Ball) -> bool:
        # Check if the ball is near the paddle in the horizontal direction (x-axis)
        if np.abs(ball.x - self.x_position) < 0.001:
            # Check if the ball is within the vertical range of the paddle
            if self.y_position - self.height / 2 - ball.radius <= ball.y <= self.y_position + self.height / 2 + ball.radius:
                return True
        return False

    def move_up(self) -> None:
        self.y_position = min(1.0 - self.height, self.y_position + self.speed)

    def move_down(self) -> None:
        self.y_position = max(0.0, self.y_position - self.speed)