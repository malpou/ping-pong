from enum import Enum

class GameState(Enum):
    WAITING = "waiting"
    PLAYING = "playing" 
    PAUSED = "paused"
    GAME_OVER = "game_over"

class GameSide(Enum):
    LEFT = "left"
    RIGHT = "right"