from typing import Dict, Optional, Set
import asyncio
from fastapi import WebSocket, HTTPException
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.orm import Session
import uuid
from domain.game import Game
from logger import logger
from networking.binary_protocol import encode_game_state, encode_game_status
from database.models import GameModel, PlayerModel
from database.config import SessionLocal, acquire_game_connection, release_game_connection
from services.games_update_service import games_update_service


class GameRoom:
    SAVE_INTERVAL = 0.2  # 5 times per second

    def __init__(self, game_id: str, db: Session):
        self.game_state = Game()
        self.game_state.room_id = game_id
        self.players: Set[WebSocket] = set()
        self.player_roles: Dict[WebSocket, str] = {}
        self.player_names: Dict[WebSocket, str] = {}  # Store player names
        self.game_id = game_id
        self.db = db
        self._save_task: Optional[asyncio.Task] = None

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

            # Broadcast new game creation
            asyncio.create_task(games_update_service.broadcast_new_game(
                self.db_game.id,
                self.game_state.state
            ))
        else:
            # Restore game state from database
            # Get just the enum value name without the 'State.' prefix
            state_name = str(self.db_game.state.value)  # This will give us e.g. 'WAITING' instead of 'State.WAITING'
            self.game_state.state = Game.State(state_name)
            self.game_state.ball.x = float(str(self.db_game.ball_x))
            self.game_state.ball.y = float(str(self.db_game.ball_y))
            self.game_state.left_paddle.y_position = float(str(self.db_game.left_paddle_y))
            self.game_state.right_paddle.y_position = float(str(self.db_game.right_paddle_y))
            self.game_state.left_score = int(str(self.db_game.left_score))
            self.game_state.right_score = int(str(self.db_game.right_score))
            self.game_state.winner = str(self.db_game.winner) if self.db_game.winner else None

    async def connect(self, websocket: WebSocket, player_name: str) -> Optional[str]:
        """Connect a player to the game room.

        Args:
            websocket: The WebSocket connection
            player_name: The name of the player

        Returns:
            Optional[str]: The role assigned to the player ('left' or 'right') or None if room is full
        """
        if len(self.players) >= 2:
            logger.warning(f"Room {self.game_id}: Connection rejected - room is full")
            return None

        # Add player to game
        self.players.add(websocket)
        role = 'left' if len(self.players) == 1 else 'right'
        self.player_roles[websocket] = role
        self.player_names[websocket] = player_name

        # Update game state
        self.game_state.add_player()

        # Add player to database
        player = PlayerModel(
            game_id=self.db_game.id,
            name=player_name,
            role=role,
            connected=True
        )
        self.db.add(player)
        self.db.commit()

        # Broadcast player joined update
        asyncio.create_task(games_update_service.broadcast_player_joined(
            self.db_game.id,
            self.game_state.state,
            self.game_state.player_count
        ))

        logger.info(
            f"Room {self.game_id}: Player {player_name} connected as {role} ({self.game_state.player_count}/2 players)")

        if self.game_state.player_count == 2:
            if not acquire_game_connection():
                self.disconnect(websocket)
                raise HTTPException(status_code=503, detail="Server at connection capacity")

            # Game state will handle transitioning to PLAYING
            self.db_game.state = self.game_state.state
            self.db.commit()

            # Start periodic state saving
            self._save_task = asyncio.create_task(self._periodic_save())

            logger.info(f"Room {self.game_id}: Game starting with 2 players")
            await self.broadcast_game_status("game_starting")
        else:
            logger.info(f"Room {self.game_id}: Waiting for more players")
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
            self.db_game.ball_x = self.game_state.ball.x
            self.db_game.ball_y = self.game_state.ball.y
            self.db_game.left_paddle_y = self.game_state.left_paddle.y_position
            self.db_game.right_paddle_y = self.game_state.right_paddle.y_position
            self.db_game.left_score = self.game_state.left_score
            self.db_game.right_score = self.game_state.right_score
            self.db_game.state = self.game_state.state
            self.db_game.winner = self.game_state.winner
            self.db.commit()
        except Exception as e:
            logger.error(f"Error saving game state for room {self.game_id}: {e}")
            self.db.rollback()

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.players:
            role = self.player_roles[websocket]
            player_name = self.player_names.get(websocket, "Unknown")
            self.players.remove(websocket)
            del self.player_roles[websocket]
            if websocket in self.player_names:
                del self.player_names[websocket]

            # Update game state
            self.game_state.remove_player()

            # Update player connection status in database
            player = self.db.query(PlayerModel).filter(
                PlayerModel.game_id == self.db_game.id,
                PlayerModel.role == role
            ).first()
            if player:
                player.connected = False
                self.db.commit()

            logger.info(f"Room {self.game_id}: Player {player_name} ({role}) disconnected ({self.game_state.player_count}/2 players)")

            if self.game_state.state == Game.State.PAUSED:
                self.db_game.state = self.game_state.state
                self.db.commit()

                # Cancel periodic saving when game is paused
                if self._save_task:
                    self._save_task.cancel()
                    release_game_connection()

                logger.info(f"Room {self.game_id}: Game paused due to player disconnect")

    async def update(self) -> None:
        previous_score = (self.game_state.left_score, self.game_state.right_score)
        previous_state = self.game_state.state

        self.game_state.update()

        if (self.game_state.left_score, self.game_state.right_score) != previous_score:
            asyncio.create_task(games_update_service.broadcast_score_update(
                uuid.UUID(self.game_id),
                self.game_state.state,
                self.game_state.player_count,
                self.game_state.left_score,
                self.game_state.right_score
            ))

        if self.game_state.state == Game.State.GAME_OVER and previous_state != Game.State.GAME_OVER:
            self.db_game.state = self.game_state.state
            self.db_game.winner = self.game_state.winner

            asyncio.create_task(games_update_service.broadcast_game_over(
                uuid.UUID(self.game_id),
                self.game_state.state,
                self.game_state.player_count,
                self.game_state.left_score,
                self.game_state.right_score,
                self.game_state.winner
            ))

            if self._save_task:
                self._save_task.cancel()
                release_game_connection()

            await self.broadcast_game_status(f"game_over_{self.game_state.winner}")

        await self.broadcast_state()

    async def broadcast_state(self) -> None:
        if not self.players:
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


class GameRoomService:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self.db = SessionLocal()

    async def create_room(self, game_id: str) -> GameRoom:  # Make method async
        if game_id not in self.rooms:
            logger.info(f"Creating new room: {game_id}")
            room = GameRoom(game_id, self.db)
            self.rooms[game_id] = room
        return self.rooms[game_id]

    def get_room(self, game_id: str) -> Optional[GameRoom]:
        return self.rooms.get(game_id)

    def remove_room(self, game_id: str) -> None:
        if game_id in self.rooms:
            room = self.rooms[game_id]
            room.cancel_save_task()
            logger.info(f"Removing room: {game_id}")
            del self.rooms[game_id]

game_room_service = GameRoomService()