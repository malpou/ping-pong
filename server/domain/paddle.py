from dataclasses import dataclass
import numpy as np
from domain.ball import Ball


@dataclass
class Paddle:
    x_position: float
    y_position: float = 0.5  # Position as percentage of screen height (0-1)
    height: float = 0.2  # Height as percentage of screen height
    width: float = 0.02 # Width of the paddle
    speed: float = 0.02  # Movement speed per frame


    def __init__(self, x_pos: float):
        self.x_position = x_pos
        self.h = self.height / 2
        self.y_min = self.y_position - self.h
        self.y_max = self.y_position + self.h

    def is_on_paddle(self, ball: Ball) -> bool:
        # Check if the ball is near the paddle in the horizontal direction (x-axis)
        if np.abs(ball.x - self.x_position) <=  ball.radius + self.width / 2:
            # Check if the ball is within the vertical range of the paddle
            if self.y_min - ball.radius <= ball.y <= self.y_max + ball.radius:
                return True
        return False

    def move_up(self) -> None:
        new_y = self.y_position - self.speed
        self.y_position = max(self.h, new_y)

    def move_down(self) -> None:
        new_y = self.y_position + self.speed
        self.y_position = min(1.0 - self.h, new_y)
