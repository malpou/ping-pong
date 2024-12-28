package server

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"pingpong/game"
	"pingpong/protocol"
)

type Server struct {
	rooms     map[string]*Room
	roomsLock sync.Mutex
	upgrader  websocket.Upgrader
}

type Room struct {
	ID      string
	Game    *game.Game
	Clients []*Client
	mu      sync.Mutex
}

type Client struct {
	Conn   *websocket.Conn
	Server *Server
	Name   string
	Room   *Room
}

func NewServer() *Server {
	return &Server{
		rooms:    make(map[string]*Room),
		upgrader: websocket.Upgrader{},
	}
}

func (s *Server) HandleConnection(w http.ResponseWriter, r *http.Request) {
	conn, err := s.upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("Upgrade error:", err)
		http.Error(w, "Could not upgrade connection", http.StatusInternalServerError)
		return
	}

	client := &Client{Conn: conn, Server: s}
	defer func() {
		if err := client.Conn.Close(); err != nil {
			log.Println("Error closing connection:", err)
		}
	}()

	client.Listen()
}

func (c *Client) Listen() {
	defer func() {
		if err := c.Conn.Close(); err != nil {
			log.Println("Error closing connection:", err)
		}
	}()

	for {
		_, message, err := c.Conn.ReadMessage()
		if err != nil {
			log.Println("Read error:", err)
			if websocket.IsCloseError(err, websocket.CloseNormalClosure) {
				log.Println("Connection closed normally")
			} else {
				log.Println("Unexpected error:", err)
			}
			break
		}
		protocol.ParseMessage(c, message)
	}
}

func (c *Client) HandleSetName(name string) {
	c.Name = name
}

func (c *Client) HandleGetGames() {
	c.Server.roomsLock.Lock()
	defer c.Server.roomsLock.Unlock()

	var rooms []string
	for roomID := range c.Server.rooms {
		rooms = append(rooms, roomID)
	}

	response := protocol.Message{
		Type: protocol.GetGamesResponse,
		Data: rooms,
	}
	c.Send(response)
}

func (c *Client) HandleJoinRoom(roomID string) {
	c.Server.roomsLock.Lock()
	room, exists := c.Server.rooms[roomID]
	c.Server.roomsLock.Unlock()

	if !exists {
		c.Send(protocol.Message{
			Type: protocol.Error,
			Data: "Room not found",
		})
		return
	}

	c.Room = room
	room.mu.Lock()
	room.Clients = append(room.Clients, c)
	room.mu.Unlock()

	room.Game.AddPlayer()

	c.Send(protocol.Message{
		Type: protocol.JoinRoomResponse,
		Data: roomID,
	})
}

func (c *Client) HandleCreateRoom() {
	room := &Room{
		ID:   generateRoomID(),
		Game: game.NewGame(),
	}

	c.Server.roomsLock.Lock()
	c.Server.rooms[room.ID] = room
	c.Server.roomsLock.Unlock()

	c.Room = room
	room.Clients = append(room.Clients, c)

	room.Game.AddPlayer()

	c.Send(protocol.Message{
		Type: protocol.CreateRoomResponse,
		Data: room.ID,
	})
}

func (c *Client) HandleMovePaddle(direction byte) {
	if c.Room == nil {
		return
	}

	c.Room.Game.MovePaddle(c.Name, direction)

	response := protocol.Message{
		Type: protocol.MovePaddleResponse,
		Data: string(direction),
	}
	c.Send(response)
}

func (c *Client) Send(message protocol.Message) {
	data, err := json.Marshal(message)
	if err != nil {
		log.Println("Error marshalling message:", err)
		return
	}

	err = c.Conn.WriteMessage(websocket.TextMessage, data)
	if err != nil {
		log.Println("Write error:", err)
	}
}

func (c *Client) GetName() string {
	return c.Name
}

func (c *Client) GetRoomID() string {
	if c.Room == nil {
		return ""
	}

	return c.Room.ID
}

func generateRoomID() string {
	return time.Now().Format("20060102150405")
}
