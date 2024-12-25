import asyncio
from typing import Set
from fastapi import WebSocket

from domain.game import Game
from networking.binary_protocol import GameUpdateType, encode_game_update
import uuid

class GamesUpdateService:
    def __init__(self):
        self._subscribers: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._subscribers.add(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._subscribers.discard(websocket)

    async def _broadcast_bytes(self, data: bytes):
        disconnected = set()
        async with self._lock:
            for subscriber in self._subscribers:
                try:
                    await subscriber.send_bytes(data)
                except:
                    disconnected.add(subscriber)
            for subscriber in disconnected:
                self._subscribers.discard(subscriber)

    async def broadcast_new_game(self, game_id: uuid.UUID, state: Game.State):
        data = encode_game_update(GameUpdateType.NEW_GAME, game_id, state, 0)
        await self._broadcast_bytes(data)

    async def broadcast_score_update(self, game_id: uuid.UUID, state: Game.State,
                                     player_count: int, left_score: int, right_score: int):
        data = encode_game_update(GameUpdateType.SCORE_UPDATE, game_id, state,
                                  player_count, left_score, right_score)
        await self._broadcast_bytes(data)

    async def broadcast_game_over(self, game_id: uuid.UUID, state: Game.State,
                                  player_count: int, left_score: int, right_score: int,
                                  winner: str):
        data = encode_game_update(GameUpdateType.GAME_OVER, game_id, state,
                                  player_count, left_score, right_score, winner)
        await self._broadcast_bytes(data)

    async def broadcast_player_joined(self, game_id: uuid.UUID, state: Game.State,
                                      player_count: int):
        data = encode_game_update(GameUpdateType.PLAYER_JOINED, game_id, state,
                                  player_count)
        await self._broadcast_bytes(data)

games_update_service = GamesUpdateService()
