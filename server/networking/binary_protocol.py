import uuid
from struct import pack, unpack
from enum import IntEnum
from typing import Optional

from domain.game import Game


class CommandType(IntEnum):
    HEARTBEAT = 0
    PADDLE_UP = 1
    PADDLE_DOWN = 2

class MessageType(IntEnum):
    GAME_STATE = 1
    GAME_STATUS = 2
    GAME_ID = 3

class GameUpdateType(IntEnum):
    NEW_GAME = 1
    SCORE_UPDATE = 2
    GAME_OVER = 3
    PLAYER_JOINED = 4

def encode_game_update(update_type: GameUpdateType, game_id: uuid.UUID,
                       state: Game.State, player_count: int,
                       left_score: int = 0, right_score: int = 0,
                       winner: str | None = None) -> bytes:
    """Encode game updates into binary format."""
    state_value = {
        Game.State.WAITING: 0,
        Game.State.PLAYING: 1,
        Game.State.PAUSED: 2,
        Game.State.GAME_OVER: 3
    }[state]

    winner_code = 0
    if winner == "left":
        winner_code = 1
    elif winner == "right":
        winner_code = 2

    return pack('!B16sBBBBB',
                       update_type.value,
                       game_id.bytes,
                       state_value,
                       player_count,
                       left_score,
                       right_score,
                       winner_code)


def decode_command(data: bytes) -> CommandType:
    """Decode binary data into a command."""
    command_value = unpack('!B', data)[0]
    return CommandType(command_value)


def encode_game_status(status: str) -> bytes:
    """Encode game status messages.
    Status can be:
    - "waiting_for_players"
    - "game_starting"
    - "game_paused"
    - "game_over"
    """
    status_bytes = status.encode('utf-8')
    return pack(f'!BB{len(status_bytes)}s',
               MessageType.GAME_STATUS,
               len(status_bytes),
               status_bytes)


def encode_game_state(ball_x: float, ball_y: float,
                      left_paddle_y: float, right_paddle_y: float,
                      left_score: int, right_score: int,
                      winner: Optional[str] = None) -> bytes:
    """Encode game state into binary format."""
    # winner_code: 0 = no winner, 1 = left won, 2 = right won
    winner_code = 0
    if winner == "left":
        winner_code = 1
    elif winner == "right":
        winner_code = 2

    return pack('!BffffBBB',
                MessageType.GAME_STATE,
                ball_x, ball_y,
                left_paddle_y, right_paddle_y,
                left_score, right_score,
                winner_code)


def encode_game_id(game_id: str) -> bytes:
    """Encode game ID message."""
    game_id_bytes = game_id.encode('utf-8')
    return pack(f'!BB{len(game_id_bytes)}s',
               MessageType.GAME_ID,
               len(game_id_bytes),
               game_id_bytes)