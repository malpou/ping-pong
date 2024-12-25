import asyncio
import os
import subprocess
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from logger import logger
from api.endpoints import endpoints
from api.websockets import handle_game_connection
from database.config import SessionLocal


class GameLoop:
    def __init__(self):
        self.rooms = {}
        self.is_running = True

    async def run(self):
        while self.is_running:
            try:
                for room in list(self.rooms.values()):
                    try:
                        await room.update()
                    except RuntimeError:
                        continue
                    except Exception as e:
                        logger.error(f"Error updating room: {e}")
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
            await asyncio.sleep(1 / 60)

    async def stop(self):
        self.is_running = False

    def add_room(self, room):
        self.rooms[str(room.game_id)] = room

    def remove_room(self, game_id):
        if str(game_id) in self.rooms:
            del self.rooms[str(game_id)]


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
    await game_loop.stop()
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
    db = SessionLocal()
    try:
        await handle_game_connection(websocket, player_name, room_id, game_loop, db)
    except Exception as e:
        try:
            await websocket.close(code=4000, reason=str(e))
        except RuntimeError:
            pass  # WebSocket already closed
    finally:
        db.close()