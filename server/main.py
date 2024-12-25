import asyncio
import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketDisconnect

from logger import logger
from api.endpoints import endpoints
from api.websockets import handle_game_connection
from services.game_room_service import game_room_service


class GameLoop:
    def __init__(self):
        self.shutdown_event = asyncio.Event()

    async def run(self):
        while not self.shutdown_event.is_set():
            try:
                for room in list(game_room_service.rooms.values()):
                    if room.players:
                        try:
                            room.game_state.update()
                            if not self.shutdown_event.is_set():
                                await room.broadcast_state()
                        except RuntimeError:
                            continue
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
            await asyncio.sleep(1 / 60)

    async def shutdown(self):
        logger.info("Application shutting down...")
        self.shutdown_event.set()

        for room_id in list(game_room_service.rooms.keys()):
            room = game_room_service.rooms[room_id]
            for player in list(room.players):
                try:
                    await player.close(code=1000, reason="Server shutting down")
                except Exception as e:
                    logger.error(f"Error closing WebSocket connection in room {room_id}: {e}")
            game_room_service.remove_room(room_id)


game_loop = GameLoop()


@asynccontextmanager
async def lifespan(_: FastAPI):
    env = {**os.environ, 'PYTHONPATH': os.getcwd()}
    try:
        subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)
    except subprocess.CalledProcessError as e:
        print(f"Failed to run migrations: {e}")
        raise

    game_loop_task = asyncio.create_task(game_loop.run())
    yield
    await game_loop.shutdown()
    game_loop_task.cancel()
    try:
        await game_loop_task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)

origins = [
    "http://localhost:5173",
    "https://ping.malpou.io",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(endpoints)
@app.websocket("/game")
async def websocket_endpoint(
        websocket: WebSocket,
        player_name: str | None = None,
        room_id: str | None = None
):
    await websocket.accept()
    try:
        await handle_game_connection(websocket, player_name, room_id, game_room_service)
    except HTTPException as e:
        try:
            await websocket.close(code=4000, reason=e.detail)
        except RuntimeError:
            pass  # WebSocket already closed

@app.websocket("/game-updates")
async def game_updates_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text("pong")
            except WebSocketDisconnect:
                break
    finally:
        await game_room_service.disconnect(websocket)