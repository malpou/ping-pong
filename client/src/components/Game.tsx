import { useCallback, useEffect, useRef, useState } from 'react';
import p5 from 'p5';
import { PongClient, GameState, GameSpecs } from '../lib/protocol';
import Particle from '../graphics/Particle';
import { Engine, Bodies, World, Body as MatterBody } from 'matter-js';
import type { Body } from 'matter-js'; // Import as type only

interface GameProps {
  playerName: string;
  gameId: string | null;
  specs: GameSpecs;
  serverUrl: string;
  onExit: () => void;
  onError: (message: string) => void;
  onGameCreated: (gameId: string) => void;
}

export function Game({ playerName, gameId, specs, serverUrl, onExit, onError, onGameCreated }: GameProps) {
  const [status, setStatus] = useState<string>('Connecting...');
  const clientRef = useRef<PongClient | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const gameStateRef = useRef<GameState | null>(null);
  const p5InstanceRef = useRef<p5 | null>(null);
  const keysPressed = useRef<Set<string>>(new Set());

  const calculateCanvasSize = useCallback(() => {
    if (!containerRef.current) return { width: 0, height: 0 };
    const container = containerRef.current;
    const aspectRatio = specs.game.bounds.width / specs.game.bounds.height;
    let width = container.clientWidth;
    let height = width / aspectRatio;
    if (height > container.clientHeight) {
      height = container.clientHeight;
      width = height * aspectRatio;
    }
    return { width, height };
  }, [specs]);

  // Handle game status updates
  const handleGameStatus = useCallback((newStatus: string) => {
    switch (newStatus) {
      case 'waiting_for_players':
        setStatus('Waiting for opponent...');
        break;
      case 'game_starting':
        setStatus('Game starting in 3...');
        break;
      case 'game_in_progress':
        setStatus('Game in progress');
        break;
      case 'game_paused':
        setStatus('Game paused - waiting for player');
        break;
      case 'game_over_left':
        setStatus('Game Over - Left player wins!');
        break;
      case 'game_over_right':
        setStatus('Game Over - Right player wins!');
        break;
      default:
        setStatus(newStatus);
    }
  }, []);

  // WebSocket connection
  useEffect(() => {
    let isSubscribed = true;

    const client = new PongClient(serverUrl, gameId, playerName);
    clientRef.current = client;

    client.onConnect = () => {
      if (!isSubscribed) return;
      setStatus('Connected');
    };

    client.onConnectError = (error) => {
      if (!isSubscribed) return;
      onError(error);
    };

    client.onDisconnect = () => {
      if (!isSubscribed) return;
      setStatus('Disconnected');
      onError('Connection lost');
    };

    client.onGameId = (newGameId) => {
      if (!isSubscribed) return;
      if (!gameId) onGameCreated(newGameId);
    };

    client.onGameStatus = (newStatus) => {
      if (!isSubscribed) return;
      handleGameStatus(newStatus);
    };

    client.onGameState = (state) => {
      if (!isSubscribed) return;
      gameStateRef.current = state;
    };

    return () => {
      isSubscribed = false;
      client.close();
      clientRef.current = null;
    };
  }, [serverUrl, gameId, playerName, onError, onGameCreated, handleGameStatus]);

  // p5.js setup and game rendering
  useEffect(() => {
    const sketch = (p: p5) => {

      const engine = Engine.create();
      const particles: Particle[] = [];

      // Paddle bodies
      let leftPaddle: Body;
      let rightPaddle: Body;

      //
      let ballBody: Body;
      
      
      p.setup = () => {
        const { width, height } = calculateCanvasSize();
        p.createCanvas(width, height);

        // Initialize paddle bodies
        const paddleWidth = width * specs.paddle.width;
        const paddleHeight = height * specs.paddle.height;

        // Left paddle body
        leftPaddle = Bodies.rectangle(
          width * specs.paddle.collision_bounds.left,
          height * specs.paddle.initial.y, // initial Y position
          paddleWidth,
          paddleHeight,
          { isStatic: true } // Make it static
        );

        // Right paddle body
        rightPaddle = Bodies.rectangle(
          width * specs.paddle.collision_bounds.right,
          height * specs.paddle.initial.y, // initial Y position
          paddleWidth,
          paddleHeight,
          { isStatic: true } // Make it static
        );

        // Ball body
        ballBody = Bodies.circle(
          specs.ball.initial.x, 
          specs.ball.initial.y, 
          specs.ball.radius,
          { isStatic: true } // Make it static
        )

        // Add paddles to the physics world
        World.add(engine.world, [leftPaddle, rightPaddle]);
        World.add(engine.world, [ballBody]);
      };

      p.draw = () => {
        p.background(0);

        Engine.update(engine);

        for (let i = particles.length - 1; i >= 0; i--) {
          if (!particles[i].update(engine)) {
            particles.splice(i, 1);
          } else {
            particles[i].show(p); // Pass the p5 instance here
          }
        }

        p.mousePressed = () => {
          for (let i = 0; i < 25; i++) {
            particles.push(new Particle(p.mouseX, p.mouseY, p.random(5, 10), p.random(150, 255), engine));
          }
        };

        const state = gameStateRef.current;
        if (!state) return;

        const scaleX = p.width;
        const scaleY = p.height;

         // Sync paddle positions
      MatterBody.setPosition(leftPaddle, {
        x: p.width * specs.paddle.collision_bounds.left,
        y: state.paddles.left * scaleY,
      });

      MatterBody.setPosition(rightPaddle, {
        x: p.width * specs.paddle.collision_bounds.right,
        y: state.paddles.right * scaleY,
      });

      // Sync ball position
      MatterBody.setPosition(ballBody, {
        x: state.ball.x * scaleX,
        y: state.ball.y * scaleY,
      });

      
        // Draw center line
        p.stroke(255, 255, 255, 100);
        p.strokeWeight(Math.max(1, p.width * 0.002));
        for (let y = 0; y < p.height; y += p.height * 0.05) {
          p.line(p.width / 2, y, p.width / 2, y + p.height * 0.025);
        }
      
        // Draw paddles
        p.noStroke();
        p.fill(255);
        const paddleWidth = p.width * specs.paddle.width;
        const paddleHeight = p.height * specs.paddle.height;
      
        // Left paddle - use initial position from specs if no state
        const leftPaddleY = state ? state.paddles.left : specs.paddle.initial.y;
        p.rect(
          p.width * specs.paddle.collision_bounds.left - paddleWidth / 2,
          leftPaddleY * scaleY - paddleHeight / 2,
          paddleWidth,
          paddleHeight
        );
      
        // Right paddle - use initial position from specs if no state
        const rightPaddleY = state ? state.paddles.right : specs.paddle.initial.y;
        p.rect(
          p.width * specs.paddle.collision_bounds.right - paddleWidth / 2,
          rightPaddleY * scaleY - paddleHeight / 2,
          paddleWidth,
          paddleHeight
        );
      
        // Draw ball - only if game state exists or use initial position
        const ballSize = p.width * specs.ball.radius * 2;
        const ballX = state ? state.ball.x : specs.ball.initial.x;
        const ballY = state ? state.ball.y : specs.ball.initial.y;
        p.ellipse(
          ballX * scaleX,
          ballY * scaleY,
          ballSize,
          ballSize
        );
      
        // Draw score - only if game state exists
        if (state) {
          const fontSize = Math.max(16, Math.min(48, p.width * 0.05));
          p.textSize(fontSize);
          p.textAlign(p.CENTER, p.CENTER);
          p.text(state.score.left.toString(), p.width * 0.25, fontSize * 1.5);
          p.text(state.score.right.toString(), p.width * 0.75, fontSize * 1.5);
        }
      
        // Handle keyboard input
        if (keysPressed.current.has('ArrowUp')) {
          clientRef.current?.sendPaddleUp();
        }
        if (keysPressed.current.has('ArrowDown')) {
          clientRef.current?.sendPaddleDown();
        }
      };

      p.windowResized = () => {
        const { width, height } = calculateCanvasSize();
        p.resizeCanvas(width, height);
      };
    };

    if (containerRef.current) {
      p5InstanceRef.current = new p5(sketch, containerRef.current);
    }

    return () => {
      if (p5InstanceRef.current) {
        p5InstanceRef.current.remove();
      }
    };
  }, [specs, calculateCanvasSize]);

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        keysPressed.current.add(e.key);
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
        e.preventDefault();
        keysPressed.current.delete(e.key);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  // Resize observer
  useEffect(() => {
    const resizeObserver = new ResizeObserver(() => {
      if (p5InstanceRef.current) {
        const { width, height } = calculateCanvasSize();
        p5InstanceRef.current.resizeCanvas(width, height);
      }
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => resizeObserver.disconnect();
  }, [calculateCanvasSize]);

  return (
    <div className="min-h-screen bg-gray-900 flex flex-col p-4">
      <div className="flex justify-between items-center mb-4">
        <div className="text-white text-lg">{status}</div>
        <button
          onClick={onExit}
          className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
        >
          Exit Game
        </button>
      </div>
      <div
        ref={containerRef}
        className="flex-1 bg-black rounded-lg shadow-lg overflow-hidden flex items-center justify-center"
      >
        {/* p5.js canvas will be inserted here */}
      </div>
      <div className="mt-4 text-gray-400 text-center">
        Use ↑ and ↓ arrow keys to move your paddle
      </div>
    </div>
  );
}