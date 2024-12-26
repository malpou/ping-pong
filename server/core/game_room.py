import time
from dataclasses import dataclass
from typing import Dict, Optional

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from domain.game import Game
from logger import logger
from networking.binary_protocol import encode_game_state, encode_game_status


@dataclass
class Player:
    name: str
    uuid: str
    role: str
    websocket: WebSocket
    connected: bool = True


class GameRoom:
    INACTIVE_TIMEOUT = 300  # 5 minutes in seconds

    def __init__(self, game_id: str):
        # Game state
        self.game_state = Game()
        self.game_state.room_id = game_id
        self.game_id = game_id

        # Room state
        self.players: Dict[str, Player] = {}  # uuid -> Player
        self.starting = False
        self.game_start_timer = None
        self.last_activity = time.time()

    @property
    def is_expired(self) -> bool:
        """Check if room should be cleaned up"""
        inactive_time = time.time() - self.last_activity
        return (inactive_time > self.INACTIVE_TIMEOUT and
                (self.game_state.state == Game.State.GAME_OVER or not self.players))

    async def connect(self, websocket: WebSocket, player_name: str, player_uuid: str) -> Optional[str]:
        """Connect a player to the game room."""
        self.last_activity = time.time()

        # Handle reconnection
        if player_uuid in self.players:
            player = self.players[player_uuid]
            if player.connected:
                logger.warning(f"Room {self.game_id}: Duplicate connection rejected for {player_name}")
                return None

            # Reconnect existing player
            player.websocket = websocket
            player.connected = True
            self.game_state.add_player()

            logger.info(f"Room {self.game_id}: Player {player_name} reconnected as {player.role}")
            await self.broadcast_game_status("player_reconnected")
            return player.role

        # Check room capacity
        connected_count = len([p for p in self.players.values() if p.connected])
        if connected_count >= 2:
            logger.warning(f"Room {self.game_id}: Connection rejected - room is full")
            return None

        # Assign role for new player
        existing_roles = {p.role for p in self.players.values() if p.connected}
        role = 'left' if 'left' not in existing_roles else 'right'

        # Add new player
        self.players[player_uuid] = Player(
            name=player_name,
            uuid=player_uuid,
            role=role,
            websocket=websocket
        )
        self.game_state.add_player()

        logger.info(f"Room {self.game_id}: Player {player_name} connected as {role}")
        await self.broadcast_game_status("waiting_for_players")
        return role

    def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a player."""
        self.last_activity = time.time()

        # Find player by websocket
        player = next((p for p in self.players.values() if p.websocket == websocket), None)
        if not player:
            return

        player.connected = False
        self.game_state.remove_player()
        logger.info(f"Room {self.game_id}: Player {player.name} ({player.role}) disconnected")

        # Update game state if needed
        connected_count = len([p for p in self.players.values() if p.connected])
        if connected_count < 2:
            self.game_state.state = Game.State.PAUSED
            logger.info(f"Room {self.game_id}: Game paused")

    async def update(self) -> None:
        """Update game state and handle game progression."""
        self.last_activity = time.time()
        previous_state = self.game_state.state
        connected_count = len([p for p in self.players.values() if p.connected])

        # Handle game start when room is full
        if connected_count == 2 and self.game_state.state == Game.State.WAITING:
            if not self.starting:
                self.starting = True
                self.game_start_timer = time.time()
                logger.info(f"Room {self.game_id}: Game starting")
                await self.broadcast_game_status("game_starting")

        # Handle countdown and game start
        if self.starting:
            elapsed = time.time() - self.game_start_timer
            if elapsed >= 3:  # 3 second countdown
                self.starting = False
                self.game_state.state = Game.State.PLAYING
                await self.broadcast_game_status("game_in_progress")
            return  # Don't update game state during countdown

        # Update game state only if playing
        if self.game_state.state == Game.State.PLAYING:
            self.game_state.update()

        # Handle state transitions
        if self.game_state.state == Game.State.PLAYING and previous_state != Game.State.PLAYING:
            await self.broadcast_game_status("game_in_progress")
        elif self.game_state.state == Game.State.PAUSED and previous_state != Game.State.PAUSED:
            await self.broadcast_game_status("game_paused")
        elif self.game_state.state == Game.State.GAME_OVER and previous_state != Game.State.GAME_OVER:
            await self.broadcast_game_status(f"game_over_{self.game_state.winner}")

        # Only broadcast state if game is playing
        if self.game_state.state == Game.State.PLAYING:
            await self.broadcast_state()

    async def broadcast_state(self) -> None:
        """Broadcast game state to all connected players."""
        if not self.players or self.game_state.state != Game.State.PLAYING:
            return

        state_bytes = encode_game_state(
            self.game_state.ball.x,
            self.game_state.ball.y,
            self.game_state.left_paddle.y_position,
            self.game_state.right_paddle.y_position,
            self.game_state.left_score,
            self.game_state.right_score,
            self.game_state.winner
        )

        disconnected_players = set()
        for player in [p for p in self.players.values() if p.connected]:
            try:
                await player.websocket.send_bytes(state_bytes)
            except (WebSocketDisconnect, RuntimeError):
                disconnected_players.add(player.uuid)
                logger.warning(f"Room {self.game_id}: Player {player.name} disconnected during state broadcast")

        # Handle any disconnections
        for player_uuid in disconnected_players:
            if player_uuid in self.players:
                self.disconnect(self.players[player_uuid].websocket)

    async def broadcast_game_status(self, status: str) -> None:
        """Broadcast game status to all connected players."""
        logger.debug(f"Room {self.game_id}: Broadcasting status - {status}")
        status_bytes = encode_game_status(status)
        disconnected_players = set()

        for player in [p for p in self.players.values() if p.connected]:
            try:
                await player.websocket.send_bytes(status_bytes)
            except WebSocketDisconnect:
                disconnected_players.add(player.uuid)
                logger.warning(f"Room {self.game_id}: Player {player.name} disconnected during status broadcast")

        # Handle any disconnections
        for player_uuid in disconnected_players:
            if player_uuid in self.players:
                self.disconnect(self.players[player_uuid].websocket)