import struct
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from domain.game import Game
from logger import logger
from networking.binary_protocol import decode_command, CommandType
import asyncio
import uuid

CONNECTION_TIMEOUT = 60  # Connection timeout in seconds
VALID_COMMANDS = {0x01, 0x02}  # Only paddle up/down commands are valid

ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server default port
    "https://ping.malpou.io",  # Production domain
]


async def handle_game_connection(
        websocket: WebSocket,
        player_name: str = Query(None),
        room_id: str | None = Query(None),
        room_manager=None
):
    """Handle WebSocket connection for a game room.
    If room_id is None, creates a new game. Otherwise joins existing game.

    Raises:
        HTTPException(400): If player_name is not provided
        HTTPException(404): If trying to join a non-existent game
    """
    # Handle CORS for WebSocket
    client_origin = websocket.headers.get('origin')
    if client_origin not in ALLOWED_ORIGINS:
        await websocket.close(code=1003, reason="Origin not allowed")
        return

    # Accept the WebSocket connection before any other processing
    await websocket.accept()

    # Validate player name
    if not player_name:
        await websocket.close(code=1000, reason="Player name is required")
        raise HTTPException(status_code=400, detail="Player name is required")

    if not room_id:
        # Create new game with random UUID
        room_id = str(uuid.uuid4())
    else:
        # Verify the room exists
        existing_room = room_manager.get_room(room_id)
        if not existing_room:
            await websocket.close(code=1000, reason="Game room not found")
            raise HTTPException(status_code=404, detail="Game room not found")

    room = await room_manager.create_room(room_id)
    player_role = None

    try:
        async with asyncio.timeout(CONNECTION_TIMEOUT):
            player_role = await room.connect(websocket, player_name)

        if not player_role:
            await websocket.close(code=1000, reason="Room is full")
            return

        # Main game loop
        while True:
            try:
                async with asyncio.timeout(CONNECTION_TIMEOUT):
                    message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if room.game_state.state != Game.State.PLAYING:
                    continue

                if message["type"] == "websocket.receive":
                    if "bytes" in message and message["bytes"]:
                        try:
                            data = message["bytes"]
                            command = decode_command(data)

                            if command == CommandType.PADDLE_UP:
                                if player_role == "left":
                                    room.game_state.left_paddle.move_up()
                                else:
                                    room.game_state.right_paddle.move_up()
                            elif command == CommandType.PADDLE_DOWN:
                                if player_role == "left":
                                    room.game_state.left_paddle.move_down()
                                else:
                                    room.game_state.right_paddle.move_down()

                        except struct.error as e:
                            logger.error(f"Error decoding command: {e}")
                            continue
                        except Exception as e:
                            logger.error(f"Unexpected error processing command: {e}")
                            continue

            except asyncio.TimeoutError:
                logger.warning("Connection timed out")
                break

    except asyncio.TimeoutError:
        logger.warning(f"Connection timeout for room {room_id}")
        await websocket.close(code=1000, reason="Connection timeout")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for room {room_id}")
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        if player_role:  # Only disconnect if the player was successfully connected
            room.disconnect(websocket)
        if not room.players:
            room_manager.remove_room(room_id)