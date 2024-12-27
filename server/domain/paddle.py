from dataclasses import dataclass
import numpy as np
from domain.ball import Ball


@dataclass
class Paddle:
    INITIAL_Y = 0.5  # Default center position
    
    x_position: float # Position as percentage of screen height (0-1)
    y_position: float = INITIAL_Y  # Position as percentage of screen height (0-1)
    height: float = 0.2  # Height as percentage of screen height
    width: float = 0.02 # Width of the paddle
    speed: float = 0.01  # Movement speed per frame

    def __init__(self, x_pos: float):
        self.x_position = x_pos
        self.h = self.height / 2

    @property
    def y_min(self) -> float:
        return self.y_position - self.h

    @property
    def y_max(self) -> float:
        return self.y_position + self.h

    def is_on_paddle(self, ball: Ball) -> bool:
        if np.abs(ball.x - self.x_position) <= ball.radius + self.width / 2:
            if self.y_min - ball.radius <= ball.y <= self.y_max + ball.radius:
                return True
        return False

    def move_up(self) -> None:
        new_y = self.y_position - self.speed
        self.y_position = max(self.h, new_y)

    def move_down(self) -> None:
        new_y = self.y_position + self.speed 
        self.y_position = min(1.0 - self.h, new_y)

    def reset_position(self) -> None:
        """Reset paddle to center position"""
        self.y_position = self.INITIAL_Y
