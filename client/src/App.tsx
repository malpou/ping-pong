import { useState, useEffect } from 'react';
import { GameList } from './components/GameList';
import { fetchGameSpecs, GameSpecs } from './lib/protocol';
import { Game } from './components/Game';
import './index.css'

const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'localhost:8000';

export default function App() {
  const [playerName, setPlayerName] = useState(localStorage.getItem('playerName') || '');
  const [gameSpecs, setGameSpecs] = useState<GameSpecs | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [gameState, setGameState] = useState<{
    id: string | null;
    isCreating: boolean;
  }>({ id: null, isCreating: false });

  useEffect(() => {
    if (playerName) {
      localStorage.setItem('playerName', playerName);
    }
  }, [playerName]);

  useEffect(() => {
    const loadSpecs = async () => {
      try {
        const specs = await fetchGameSpecs(SERVER_URL);
        setGameSpecs(specs);
      } catch (err) {
        setError('Failed to load game specifications');
      }
    };
    loadSpecs();
  }, []);

  const handleExitGame = () => {
    setGameState({ id: null, isCreating: false });
  };

  const handleJoinGame = (gameId: string) => {
    setGameState({ id: gameId, isCreating: false });
  };

  const handleCreateGame = () => {
    setGameState({ id: null, isCreating: true });
  };

  if (!gameSpecs) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="text-white text-lg">
          {error || 'Loading game specifications...'}
        </div>
      </div>
    );
  }

  if (!playerName) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-900">
        <div className="bg-gray-800 p-8 rounded-lg shadow-lg w-96">
          <h1 className="text-2xl text-white mb-4">Welcome to Pong!</h1>
          <form onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            const name = formData.get('name') as string;
            if (name.trim()) {
              setPlayerName(name.trim());
            }
          }}>
            <input
              type="text"
              name="name"
              placeholder="Enter your name"
              className="w-full p-2 mb-4 rounded bg-gray-700 text-white"
              required
            />
            <button
              type="submit"
              className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700"
            >
              Start Playing
            </button>
          </form>
        </div>
      </div>
    );
  }

  // In game or creating game
  if (gameState.id || gameState.isCreating) {
    return (
      <Game
        playerName={playerName}
        gameId={gameState.isCreating ? null : gameState.id}
        specs={gameSpecs}
        serverUrl={SERVER_URL}
        onExit={handleExitGame}
      />
    );
  }

  // Game list view
  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl text-white">Welcome, {playerName}!</h1>
          <button
            onClick={() => setPlayerName('')}
            className="text-gray-400 hover:text-white"
          >
            Change Name
          </button>
        </div>
        <GameList
          serverUrl={SERVER_URL}
          onJoinGame={handleJoinGame}
          onCreateGame={handleCreateGame}
        />
      </div>
    </div>
  );
}