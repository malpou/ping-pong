import { useEffect, useState } from 'react';
import { fetchGames } from '../lib/protocol';

interface Game {
  id: string;
  state: string;
  player_count: number;
  left_score: number;
  right_score: number;
  winner: string | null;
  created_at: string;
  updated_at: string;
}

interface GameListProps {
  serverUrl: string;
  onJoinGame: (gameId: string) => void;
  onCreateGame: () => void;
}

export function GameList({ serverUrl, onJoinGame, onCreateGame }: GameListProps) {
  const [games, setGames] = useState<Game[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadGames = async () => {
      try {
        const gameList = await fetchGames(serverUrl);
        setGames(gameList);
        setError(null);
      } catch (err) {
        setError('Failed to load games');
      }
    };

    loadGames();
    const interval = setInterval(loadGames, 5000);
    return () => clearInterval(interval);
  }, [serverUrl]);

  function getStateDisplay(state: string, playerCount: number) {
    switch (state) {
      case 'WAITING':
        return <span className="text-yellow-500">Waiting ({playerCount}/2)</span>;
      case 'PLAYING':
        return <span className="text-green-500">In Progress</span>;
      case 'PAUSED':
        return <span className="text-orange-500">Paused</span>;
      case 'GAME_OVER':
        return <span className="text-red-500">Finished</span>;
      default:
        return <span className="text-gray-500">{state}</span>;
    }
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl text-white">Available Games</h2>
        <button
          onClick={onCreateGame}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
        >
          Create New Game
        </button>
      </div>

      {error && (
        <div className="bg-red-600 text-white p-4 rounded mb-4">
          {error}
        </div>
      )}

      <div className="grid gap-4">
        {games.map((game) => (
          <div
            key={game.id}
            className="bg-gray-800 p-4 rounded-lg shadow flex justify-between items-center"
          >
            <div>
              <div className="text-white mb-1">
                Game {game.id.split('-')[0]}
              </div>
              <div className="text-sm text-gray-400">
                {getStateDisplay(game.state, game.player_count)}
              </div>
              {game.state === 'PLAYING' && (
                <div className="text-sm text-gray-400 mt-1">
                  Score: {game.left_score} - {game.right_score}
                </div>
              )}
            </div>
            <button
              onClick={() => onJoinGame(game.id)}
              disabled={game.state === 'GAME_OVER' || game.player_count >= 2}
              className={`px-4 py-2 rounded ${
                game.state === 'GAME_OVER' || game.player_count >= 2
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {game.state === 'GAME_OVER'
                ? 'Game Over'
                : game.player_count >= 2
                ? 'Full'
                : 'Join Game'}
            </button>
          </div>
        ))}

        {games.length === 0 && !error && (
          <div className="text-gray-400 text-center py-8">
            No games available. Create a new game to start playing!
          </div>
        )}
      </div>
    </div>
  );
}