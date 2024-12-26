import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import endpoints
from api.game_socket_handler import handle_game_connection
from core.game_loop import game_loop


@asynccontextmanager
async def lifespan(_: FastAPI):
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
        room_id: str | None = None,
        player_uuid: str | None = None,
):
    await websocket.accept()
    try:
        await handle_game_connection(websocket, player_name, room_id, player_uuid, game_loop)
    except Exception as e:
        try:
            await websocket.close(code=4000, reason=str(e))
        except RuntimeError:
            pass  # WebSocket already closed
