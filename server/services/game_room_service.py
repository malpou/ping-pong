import time
from typing import Dict, Optional, Set
import asyncio
from fastapi import WebSocket, HTTPException
from starlette.websockets import WebSocketDisconnect
import uuid
from domain.game import Game
from logger import logger
from networking.binary_protocol import encode_game_state, encode_game_status
from database.models import GameModel, PlayerModel
from database.config import SessionLocal, acquire_game_connection, release_game_connection


class GameRoom:
    SAVE_INTERVAL = 0.2  # 5 times per second

    def __init__(self, game_id: str, db):
        self.game_state = Game()
        self.game_state.room_id = game_id
        self.players: Set[WebSocket] = set()
        self.player_roles: Dict[WebSocket, str] = {}
        self.player_names: Dict[WebSocket, str] = {}
        self.game_id = game_id
        self.db = db
        self._save_task: Optional[asyncio.Task] = None
        self.game_start_timer = None  
        self.starting = False 


        # Create or get game from database
        self.db_game = self.db.query(GameModel).filter(GameModel.id == uuid.UUID(game_id)).first()
        if not self.db_game:
            self.db_game = GameModel(
                id=uuid.UUID(game_id),
                state=self.game_state.state,
                ball_x=self.game_state.ball.x,
                ball_y=self.game_state.ball.y,
                left_paddle_y=self.game_state.left_paddle.y_position,
                right_paddle_y=self.game_state.right_paddle.y_position
            )
            self.db.add(self.db_game)
            self.db.commit()
        else:
            # Restore game state from database
            state_name = str(self.db_game.state.value)
            self.game_state.state = Game.State(state_name)
            self.game_state.ball.x = float(str(self.db_game.ball_x))
            self.game_state.ball.y = float(str(self.db_game.ball_y))
            self.game_state.left_paddle.y_position = float(str(self.db_game.left_paddle_y))
            self.game_state.right_paddle.y_position = float(str(self.db_game.right_paddle_y))
            self.game_state.left_score = int(str(self.db_game.left_score))
            self.game_state.right_score = int(str(self.db_game.right_score))
            self.game_state.winner = str(self.db_game.winner) if self.db_game.winner else None

    async def connect(self, websocket: WebSocket, player_name: str) -> Optional[str]:
        """Connect a player to the game room."""
        connected_players = len([p for p in self.db_game.players if p.connected])

        if connected_players >= 2:
            logger.warning(f"Room {self.game_id}: Connection rejected - room is full")
            return None

        # Check existing roles and assign new role 
        existing_roles = {p.role for p in self.db_game.players if p.connected}
        role = 'left' if 'left' not in existing_roles else 'right'

        # Add player to game state
        self.players.add(websocket)
        self.player_roles[websocket] = role 
        self.player_names[websocket] = player_name
        self.game_state.add_player()

        # Create player in DB
        player = PlayerModel(
            game_id=self.db_game.id,
            name=player_name,
            role=role,
            connected=True
        )
        self.db.add(player)
        self.db.commit()

        logger.info(f"Room {self.game_id}: Player {player_name} connected as {role}")
        
        # Initially broadcast waiting status
        await self.broadcast_game_status("waiting_for_players")

        return role

    async def _periodic_save(self):
        try:
            while self.game_state.state == Game.State.PLAYING:
                self._save_state_to_db()
                await asyncio.sleep(self.SAVE_INTERVAL)
        except Exception as e:
            logger.error(f"Error in periodic save for room {self.game_id}: {e}")
        finally:
            self._save_state_to_db()

    def _save_state_to_db(self):
        try:
            self.db_game.ball_x = float(self.game_state.ball.x)
            self.db_game.ball_y = float(self.game_state.ball.y)
            self.db_game.left_paddle_y = float(self.game_state.left_paddle.y_position)
            self.db_game.right_paddle_y = float(self.game_state.right_paddle.y_position)
            self.db_game.left_score = int(self.game_state.left_score)
            self.db_game.right_score = int(self.game_state.right_score)
            self.db_game.state = self.game_state.state
            self.db_game.winner = self.game_state.winner
            self.db.commit()
        except Exception as e:
            logger.error(f"Error saving game state for room {self.game_id}: {e}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a player from the game room."""
        if websocket in self.players:
            # Clean up player data
            role = self.player_roles[websocket]
            player_name = self.player_names.get(websocket, "Unknown")
            self.players.remove(websocket)
            del self.player_roles[websocket]
            del self.player_names[websocket]

            # Update game state
            self.game_state.remove_player()

            # Update DB
            player = self.db.query(PlayerModel).filter(
                PlayerModel.game_id == self.db_game.id,
                PlayerModel.role == role
            ).first()
            if player:
                player.connected = False
                self.db.commit()

            logger.info(f"Room {self.game_id}: Player {player_name} ({role}) disconnected")

            # Handle game pause
            if self.game_state.state == Game.State.PAUSED:
                self.db_game.state = self.game_state.state
                self.db.commit()

                if self._save_task:
                    self._save_task.cancel()
                    release_game_connection()

                logger.info(f"Room {self.game_id}: Game paused")

            # Clean up tasks if no players left
            if not self.players:
                self.cancel_tasks()

    async def update(self) -> None:
        """Update game state and handle game progression."""
        previous_state = self.game_state.state
        connected_players = len([p for p in self.db_game.players if p.connected])

        # Handle game start when room is full
        if connected_players == 2 and self.game_state.state == Game.State.WAITING:
            if not self.starting:
                self.starting = True
                self.game_start_timer = time.time()
                if acquire_game_connection():
                    logger.info(f"Room {self.game_id}: Game starting")
                    await self.broadcast_game_status("game_starting")
                    self._save_task = asyncio.create_task(self._periodic_save())
                else:
                    self.starting = False
                    raise HTTPException(status_code=503, detail="Server at capacity")

        # Handle countdown and game start
        if self.starting:
            elapsed = time.time() - self.game_start_timer
            if elapsed >= 3:  # 3 second countdown
                self.starting = False
                self.game_state.state = Game.State.PLAYING
                self.db_game.state = self.game_state.state
                self.db.commit()
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
            self.db_game.state = self.game_state.state
            self.db_game.winner = self.game_state.winner
            if self._save_task:
                self._save_task.cancel()
                release_game_connection()
            await self.broadcast_game_status(f"game_over_{self.game_state.winner}")

        # Only broadcast state if game is playing
        if self.game_state.state == Game.State.PLAYING:
            await self.broadcast_state()

    async def broadcast_state(self) -> None:
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
        for player in list(self.players):
            try:
                await player.send_bytes(state_bytes)
            except (WebSocketDisconnect, RuntimeError):
                disconnected_players.add(player)

        for player in disconnected_players:
            self.disconnect(player)

    async def broadcast_game_status(self, status: str) -> None:
        logger.debug(f"Room {self.game_id}: Broadcasting status - {status}")
        status_bytes = encode_game_status(status)
        disconnected_players = set()

        for player in self.players:
            try:
                await player.send_bytes(status_bytes)
            except WebSocketDisconnect:
                disconnected_players.add(player)
                logger.warning(f"Room {self.game_id}: Player disconnected during status broadcast")

        # Handle any disconnections
        for player in disconnected_players:
            self.disconnect(player)

    def cancel_save_task(self) -> None:
        """Cancel the periodic save task if it exists and is running."""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            release_game_connection()

    def cancel_tasks(self) -> None:
        if self._save_task:
            self._save_task.cancel()
            release_game_connection()