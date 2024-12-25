function getProtocols(server: string) {
  const isLocalhost = server.includes('localhost') || server.includes('127.0.0.1');
  return {
    ws: isLocalhost ? 'ws' : 'wss',
    http: isLocalhost ? 'http' : 'https'
  };
}

export interface GameState {
  ball: {
    x: number;
    y: number;
  };
  paddles: {
    left: number;
    right: number;
  };
  score: {
    left: number;
    right: number;
  };
  winner: 'left' | 'right' | null;
}

export interface GameSpecs {
  ball: {
    radius: number;
    initial: { x: number; y: number; }
  };
  paddle: {
    height: number;
    width: number;
    initial: { y: number; };
    collision_bounds: {
      left: number;
      right: number;
    }
  };
  game: {
    points_to_win: number;
    bounds: {
      width: number;
      height: number;
    }
  }
}

export class PongClient {
  private ws: WebSocket;

  onGameState?: (state: GameState) => void;
  onGameStatus?: (status: string) => void;
  onGameId?: (gameId: string) => void;
  onConnect?: () => void;
  onConnectError?: (error: string) => void;
  onDisconnect?: () => void;

  constructor(server: string, roomId: string | null, playerName: string) {
    const params = new URLSearchParams();
    params.append('player_name', playerName);
    if (roomId) {
      params.append('room_id', roomId);
    }

    const { ws: protocol } = getProtocols(server);
    const wsUrl = `${protocol}://${server}/game?${params.toString()}`;
    
    this.ws = new WebSocket(wsUrl);
    this.ws.binaryType = 'arraybuffer';
    this.setupHandlers();
  }

  private setupHandlers() {
    this.ws.onopen = () => this.onConnect?.();
    
    this.ws.onerror = () => {
      this.onConnectError?.('Failed to connect to game server');
    };
    
    this.ws.onclose = (event) => {
      if (event.code === 1000) {
        if (event.reason === "Game room not found") {
          this.onConnectError?.('Game not found');
        } else if (event.reason === "Room is full") {
          this.onConnectError?.('Game is full');
        }
      }
      this.onDisconnect?.();
    };

    this.ws.onmessage = (event) => {
      const data = new DataView(event.data);
      const messageType = data.getUint8(0);

      switch (messageType) {
        case 0x01: // Game State
          this.handleGameState(data);
          break;
        case 0x02: // Game Status
          this.handleGameStatus(data);
          break;
        case 0x03: // Game ID
          this.handleGameId(data);
          break;
      }
    };
  }

  private handleGameId(data: DataView) {
    const length = data.getUint8(1);
    const decoder = new TextDecoder();
    const gameId = decoder.decode(new Uint8Array(data.buffer, 2, length));
    this.onGameId?.(gameId);
  }

  private handleGameStatus(data: DataView) {
    const length = data.getUint8(1);
    const decoder = new TextDecoder();
    const status = decoder.decode(new Uint8Array(data.buffer, 2, length));
    
    // Check if game is over
    if (status.startsWith('game_over')) {
      this.clearStoredGameId();
    }
    
    this.onGameStatus?.(status);
  }

  private clearStoredGameId() {
    localStorage.removeItem('currentGameId');
  }

  private handleGameState(data: DataView) {
    const gameState: GameState = {
      ball: {
        x: data.getFloat32(1, false),
        y: data.getFloat32(5, false)
      },
      paddles: {
        left: data.getFloat32(9, false),
        right: data.getFloat32(13, false)
      },
      score: {
        left: data.getUint8(17),
        right: data.getUint8(18)
      },
      winner: (() => {
        const winnerCode = data.getUint8(19);
        switch (winnerCode) {
          case 1: return 'left';
          case 2: return 'right';
          default: return null;
        }
      })()
    };
    this.onGameState?.(gameState);
  }

  public sendPaddleUp() {
    if (this.ws.readyState === WebSocket.OPEN) {
      const command = new Uint8Array([0x01]);
      this.ws.send(command);
    }
  }

  public sendPaddleDown() {
    if (this.ws.readyState === WebSocket.OPEN) {
      const command = new Uint8Array([0x02]);
      this.ws.send(command);
    }
  }

  public close() {
    this.ws.close();
}
}

export async function fetchGameSpecs(server: string): Promise<GameSpecs> {
  const { http: protocol } = getProtocols(server);
  const response = await fetch(`${protocol}://${server}/specs`);
  if (!response.ok) throw new Error('Failed to fetch game specifications');
  return await response.json();
}

export async function fetchGames(server: string) {
  const { http: protocol } = getProtocols(server);
  const response = await fetch(`${protocol}://${server}/games`);
  if (!response.ok) throw new Error('Failed to fetch games');
  return await response.json();
}