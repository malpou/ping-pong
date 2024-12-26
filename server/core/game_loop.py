import asyncio
from typing import Dict

from core.game_room import GameRoom
from logger import logger


class GameLoop:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}
        self.is_running = True

    async def run(self):
        while self.is_running:
            try:
                # Clean up expired rooms
                expired = [room_id for room_id, room in self.rooms.items() if room.is_expired]
                for room_id in expired:
                    del self.rooms[room_id]
                    logger.info(f"Removed expired room {room_id}")

                # Update active rooms
                for room in list(self.rooms.values()):
                    try:
                        await room.update()
                    except Exception as e:
                        logger.error(f"Error updating room: {e}")
            except Exception as e:
                logger.error(f"Error in game loop: {e}")
            await asyncio.sleep(1/60)

    async def stop(self):
        """Stop game loop and clean up resources."""
        self.is_running = False
        # Clean up all rooms
        for room_id in list(self.rooms.keys()):
            del self.rooms[room_id]

    def add_room(self, room):
        self.rooms[str(room.game_id)] = room

    def remove_room(self, game_id):
        if str(game_id) in self.rooms:
            del self.rooms[str(game_id)]

game_loop = GameLoop()