import asyncio
import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from logger import logger
from api.endpoints import endpoints
from api.websockets import handle_game_connection

from networking.game_room_manager import game_room_manager
from networking.game_update_manager import game_update_manager


class GameLoop:
    def __init__(self):
        self.shutdown_event = asyncio.Event()

    async def run(self):
        """Run the game loop until shutdown event is set."""
        while not self.shutdown_event.is_set():
            try:
                for room in list(game_room_manager.rooms.values()):
                    if room.players:
                        try:
                            room.game_state.update()
                            if not self.shutdown_event.is_set():
                                await room.broadcast_state()
                        except RuntimeError:
                            continue
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
            await asyncio.sleep(1 / 60)  # 60 FPS

    async def shutdown(self):
        """Gracefully shutdown the game loop."""
        logger.info("Application shutting down...")
        self.shutdown_event.set()

        for room_id in list(game_room_manager.rooms.keys()):
            room = game_room_manager.rooms[room_id]
            for player in list(room.players):
                try:
                    await player.close(code=1000, reason="Server shutting down")
                except Exception as e:
                    logger.error(f"Error closing WebSocket connection in room {room_id}: {e}")
            game_room_manager.remove_room(room_id)


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

# Configure CORS
origins = [
    "http://localhost:5173",    # Vite dev server default port
    "https://ping.malpou.io",   # Production domain
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],        # Allows all methods
    allow_headers=["*"],        # Allows all headers
)

app.include_router(endpoints)


@app.websocket("/game")
async def websocket_endpoint(
        websocket: WebSocket,
        player_name: str | None = None,
        room_id: str | None = None
):
    """WebSocket endpoint for game connections.

    Raises:
        HTTPException(400): If player_name is not provided
        HTTPException(404): If trying to join a non-existent game
    """
    try:
        await handle_game_connection(websocket, player_name, room_id, game_room_manager)
    except HTTPException as e:
        # Log the error and let the websocket close handle the rest
        logger.error(f"HTTP Error in websocket connection: {e.detail}")
        return


@app.websocket("/game-updates")
async def game_updates_endpoint(websocket: WebSocket):
    """WebSocket endpoint for receiving game updates."""
    try:
        await game_update_manager.connect(websocket)
        while True:
            try:
                # Keep the connection alive and check for client disconnection
                message = await websocket.receive_text()
                if message == "ping":
                    await websocket.send_text("pong")
            except Exception as _:
                break
    finally:
        await game_update_manager.disconnect(websocket)