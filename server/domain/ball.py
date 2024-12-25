from dataclasses import dataclass

import numpy as np


@dataclass
class Ball:
    x: float = 0.5  # Position as percentage of screen width
    y: float = 0.5  # Position as percentage of screen height
    angle: float = 0  # Velocity angle
    speed: float = 1 / 60 * 1 / 3  # Velocity norm
    radius: float = 0.02  # Radius as percentage of screen width

    def update_position(self) -> None:
        self.x, self.y = self.calc_pos()

        # Bounce off top and bottom
        if self.y <= 0 or self.y >= 1:
            self.angle = -self.angle

    def calc_pos(self):
        v_x = self.speed * np.cos(self.angle)
        v_y = self.speed * np.sin(self.angle)

        x = self.x + v_x
        y = self.y + v_y

        return x, y

    def reset(self) -> None:
        self.x = 0.5
        self.y = 0.5
        self.angle = 0