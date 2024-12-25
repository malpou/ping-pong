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
    HEARTBEAT_TIMEOUT = 5  # seconds

    def __init__(self, game_id: str, db: Session):
        self.game_state = Game()
        self.game_state.room_id = game_id
        self.players: Set[WebSocket] = set()
        self.player_roles: Dict[WebSocket, str] = {}
        self.player_names: Dict[WebSocket, str] = {}  # Store player names
        self.last_heartbeat: Dict[WebSocket, float] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None
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
        """Connect a player to the game room."""
        connected_players = len([p for p in self.db_game.players if p.connected])

        # Check if player already exists in this game
        existing_player = next((p for p in self.db_game.players if p.name == player_name and p.connected), None)
        if existing_player:
            # Update existing player's connection
            old_socket = next((ws for ws, name in self.player_names.items() if name == player_name), None)
            if old_socket:
                old_role = self.player_roles[old_socket]
                self.players.remove(old_socket)
                del self.player_roles[old_socket]
                del self.player_names[old_socket]
                if old_socket in self.last_heartbeat:
                    del self.last_heartbeat[old_socket]

            # Add new connection with same role
            self.players.add(websocket)
            self.player_roles[websocket] = existing_player.role
            self.player_names[websocket] = player_name
            self.last_heartbeat[websocket] = asyncio.get_event_loop().time()

            logger.info(f"Room {self.game_id}: Player {player_name} reconnected as {existing_player.role}")
            return existing_player.role

        # Regular new player connection logic
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

        # Setup heartbeat tracking
        self.last_heartbeat[websocket] = asyncio.get_event_loop().time()
        if len(self.players) == 1:
            self._heartbeat_task = asyncio.create_task(self._check_heartbeats())

        # Broadcast join
        asyncio.create_task(games_update_service.broadcast_player_joined(
            self.db_game.id, self.game_state.state, connected_players + 1
        ))
        logger.info(f"Room {self.game_id}: Player {player_name} connected as {role}")

        # Handle game start if room full
        if connected_players + 1 >= 2:
            if not acquire_game_connection():
                self.disconnect(websocket)
                raise HTTPException(status_code=503, detail="Server at capacity")

            self.game_state.state = Game.State.PLAYING
            self.db_game.state = self.game_state.state
            self.db.commit()
            self._save_task = asyncio.create_task(self._periodic_save())

            logger.info(f"Room {self.game_id}: Game starting")
            await self.broadcast_game_status("game_starting")
            await asyncio.sleep(3)
            if self.game_state.state == Game.State.PLAYING:
                await self.broadcast_game_status("game_in_progress")
        else:
            logger.info(f"Room {self.game_id}: Waiting for players")
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
            self.db.rollback()

    def disconnect(self, websocket: WebSocket) -> None:
        """Disconnect a player from the game room."""
        if websocket in self.players:
            # Clean up player data
            role = self.player_roles[websocket]
            player_name = self.player_names.get(websocket, "Unknown")
            self.players.remove(websocket)
            del self.player_roles[websocket]
            del self.player_names[websocket]
            if websocket in self.last_heartbeat:
                del self.last_heartbeat[websocket]

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
        previous_score = (self.game_state.left_score, self.game_state.right_score)
        previous_state = self.game_state.state

        self.game_state.update()

        # Send appropriate status messages based on game state
        if self.game_state.state == Game.State.PLAYING and previous_state != Game.State.PLAYING:
            await self.broadcast_game_status("game_in_progress")
        elif self.game_state.state == Game.State.PAUSED and previous_state != Game.State.PAUSED:
            await self.broadcast_game_status("game_paused")

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

    async def update_heartbeat(self, websocket: WebSocket) -> None:
        self.last_heartbeat[websocket] = asyncio.get_event_loop().time()

    async def _check_heartbeats(self) -> None:
        while self.players:
            try:
                current_time = asyncio.get_event_loop().time()
                disconnected_players = set()

                for player, last_beat in self.last_heartbeat.items():
                    if current_time - last_beat > self.HEARTBEAT_TIMEOUT:
                        disconnected_players.add(player)

                for player in disconnected_players:
                    logger.info(f"Player disconnected due to heartbeat timeout")
                    self.disconnect(player)

                await asyncio.sleep(1)  # Check every second
            except Exception as e:
                logger.error(f"Error in heartbeat check: {e}")

    def cancel_tasks(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._save_task:
            self._save_task.cancel()
            release_game_connection()


class GameRoomService:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self.updates_clients: Set[WebSocket] = set()
        self.db = SessionLocal()

    async def create_room(self, game_id: str) -> GameRoom:
        if game_id not in self.rooms:
            existing_game = self.db.query(GameModel).filter(GameModel.id == uuid.UUID(game_id)).first()
            if existing_game:
                logger.info(f"Restoring room from database: {game_id}")
                room = GameRoom(game_id, self.db)
            else:
                logger.info(f"Creating new room: {game_id}")
                room = GameRoom(game_id, self.db)
            self.rooms[game_id] = room
        return self.rooms[game_id]

    def get_room(self, game_id: str) -> Optional[GameRoom]:
        if game_id in self.rooms:
            return self.rooms[game_id]

        existing_game = self.db.query(GameModel).filter(GameModel.id == uuid.UUID(game_id)).first()
        if existing_game:
            logger.info(f"Restoring room from database: {game_id}")
            room = GameRoom(game_id, self.db)
            self.rooms[game_id] = room
            return room

        return None

    def remove_room(self, game_id: str) -> None:
        if game_id in self.rooms:
            room = self.rooms[game_id]
            room.cancel_save_task()
            logger.info(f"Removing room from memory: {game_id}")
            del self.rooms[game_id]

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.updates_clients.add(websocket)
        logger.info("Client connected to game updates endpoint")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.updates_clients:
            self.updates_clients.remove(websocket)
            logger.info("Client disconnected from game updates endpoint")

game_room_service = GameRoomService()