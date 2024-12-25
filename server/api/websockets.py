import struct
from fastapi import WebSocket, WebSocketDisconnect, Query, HTTPException
from domain.game import Game
from logger import logger
from networking.binary_protocol import decode_command, CommandType, encode_game_id
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
    room = None
    player_role = None

    try:
        client_origin = websocket.headers.get('origin')
        if client_origin not in ALLOWED_ORIGINS:
            await websocket.close(code=1003, reason="Origin not allowed")
            return

        if not player_name:
            raise HTTPException(status_code=400, detail="Player name is required")

        if room_id:
            existing_room = room_manager.get_room(room_id)
            if not existing_room:
                raise HTTPException(status_code=404, detail="Game room not found")

        if not room_id:
            room_id = str(uuid.uuid4())

        room = await room_manager.create_room(room_id)
        player_role = await room.connect(websocket, player_name)

        if not player_role:
            raise HTTPException(status_code=409, detail="Room is full")

        await websocket.send_bytes(encode_game_id(room.game_id))

        while True:
            async with asyncio.timeout(CONNECTION_TIMEOUT):
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if message["type"] == "websocket.receive" and "bytes" in message:
                    try:
                        command = decode_command(message["bytes"])

                        if command == CommandType.HEARTBEAT:
                            await room.update_heartbeat(websocket)
                            continue

                        if room.game_state.state != Game.State.PLAYING:
                            continue

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

                    except (struct.error, Exception) as e:
                        logger.error(f"Error processing command: {e}")
                        continue

    except asyncio.TimeoutError:
        logger.warning(f"Connection timeout for room {room_id}")
        raise HTTPException(status_code=408, detail="Connection timeout")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for room {room_id}")
    except Exception as e:
        logger.error(f"Error in websocket connection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if room and player_role:
            room.disconnect(websocket)
            if not room.players:
                room_manager.remove_room(room_id)