from dataclasses import dataclass
import numpy as np

from domain.enums import GameSide


@dataclass
class Ball:
    x: float = 0.5  # Position as percentage of screen width
    y: float = 0.5  # Position as percentage of screen height
    angle: float = 0  # Velocity angle
    speed: float = None  # Will be set by Game class
    radius: float = 0.02  # Radius as percentage of screen width
    first_serve: bool = True

    def __post_init__(self):
        if self.speed is None:
            self.speed = 1/60 * 1/2  # Default speed if not set by Game

    def set_speed(self, new_speed: float) -> None:
        self.speed = new_speed

    def normalize_angle(self, angle) -> float:
        return np.mod(angle, 2 * np.pi)

    def update_position(self) -> None:
        self.x, self.y = self.calc_pos()

        # Bounce off top and bottom
        if (
                ((self.y <= self.radius) and (np.pi <= self.angle <= 2 * np.pi)) or
                ((self.y >= 1 - self.radius) and (0 <= self.angle <= np.pi))
        ):
            self.angle = self.normalize_angle(-self.angle)

    def calc_pos(self):
        v_x = self.speed * np.cos(self.angle)
        v_y = self.speed * np.sin(self.angle)

        x = self.x + v_x
        y = self.y + v_y

        return x, y

    def set_direction(self, direction: GameSide = None) -> None:
        if direction == GameSide.LEFT:
            self.angle = np.pi  # Towards left
        elif direction == GameSide.RIGHT:
            self.angle = 0  # Towards right
        else:
            # Random first serve
            self.angle = np.random.choice([0, np.pi])

    def reset(self, direction: GameSide = None) -> None:
        self.x = 0.5
        self.y = 0.5
        if self.first_serve:
            self.set_direction()
            self.first_serve = False
        else:
            self.set_direction(direction)