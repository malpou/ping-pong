import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate, useParams, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { GameList } from './components/GameList';
import { fetchGameSpecs, GameSpecs } from './lib/protocol';
import { Game } from './components/Game';
import './index.css';

const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'localhost:8000';

function GameWrapper() {
  const navigate = useNavigate();
  const { gameId } = useParams();
  const playerName = localStorage.getItem('playerName');
  const [specs, setSpecs] = useState<GameSpecs | null>(null);

  useEffect(() => {
    if (!playerName) {
      navigate('/');
      return;
    }

    const loadSpecs = async () => {
      try {
        const specs = await fetchGameSpecs(SERVER_URL);
        setSpecs(specs);
      } catch (err) {
        navigate('/', { state: { error: 'Failed to load game specifications' } });
      }
    };
    loadSpecs();
  }, [navigate, playerName]);

  if (!specs || !playerName) return null;

  return (
    <Game
      playerName={playerName}
      gameId={gameId || null}
      specs={specs}
      serverUrl={SERVER_URL}
      onExit={() => navigate('/')}
      onError={(message) => {
        navigate('/', { state: { error: message } });
      }}
      onGameCreated={(newGameId) => {
        navigate(`/game/${newGameId}`);
      }}
    />
  );
}

function MainMenu() {
  const navigate = useNavigate();
  const [playerName, setPlayerName] = useState(localStorage.getItem('playerName') || '');
  const [gameSpecs, setGameSpecs] = useState<GameSpecs | null>(null);
  const { state } = useLocation();
  const [error, setError] = useState<string | null>(state?.error || null);

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
              localStorage.setItem('playerName', name.trim());
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

  return (
    <div className="min-h-screen bg-gray-900 p-8">
      <div className="max-w-4xl mx-auto">
        {error && (
          <div className="bg-red-600 text-white p-4 rounded mb-4">
            {error}
          </div>
        )}
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-2xl text-white">Welcome, {playerName}!</h1>
          <button
            onClick={() => {
              localStorage.removeItem('playerName');
              setPlayerName('');
            }}
            className="text-gray-400 hover:text-white"
          >
            Change Name
          </button>
        </div>
        <GameList
          serverUrl={SERVER_URL}
          onJoinGame={(gameId) => navigate(`/game/${gameId}`)}
          onCreateGame={() => navigate('/game')}
        />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainMenu />} />
        <Route path="/game" element={<GameWrapper />} />
        <Route path="/game/:gameId" element={<GameWrapper />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}