package protocol

import (
	"encoding/json"
	"log"
	"pingpong/game"
)

const (
	SetName            = "set_name"
	GetGames           = "get_games"
	JoinRoom           = "join_room"
	CreateRoom         = "create_room"
	MovePaddle         = "move_paddle"
	GetGamesResponse   = "get_games_response"
	JoinRoomResponse   = "join_room_response"
	CreateRoomResponse = "create_room_response"
	MovePaddleResponse = "move_paddle_response"
	Error              = "error"
)

type Message struct {
	Type string      `json:"type"`
	Data interface{} `json:"data"`
}

type ClientActions interface {
	HandleSetName(name string)
	HandleGetGames()
	HandleJoinRoom(roomID string)
	HandleCreateRoom()
	HandleMovePaddle(direction game.Direction)
	GetName() string
	GetRoomID() string
	Send(msg Message)
}

// ParseMessage processes the incoming message and handles errors.
func ParseMessage(client ClientActions, rawMessage []byte) {
	var message Message
	err := json.Unmarshal(rawMessage, &message)
	if err != nil {
		log.Println("Error parsing message:", err)
		return
	}

	var errorMessage Message
	errorMessage.Type = "error"

	// Check if the client's name is set
	if client.GetName() == "" && message.Type != SetName {
		errorMessage.Data = "Name must be set first"
		client.Send(errorMessage)
		return
	}

	// Check for missing name data
	if message.Type == SetName {
		if name, ok := message.Data.(string); !ok || name == "" {
			errorMessage.Data = "Name cannot be empty"
			client.Send(errorMessage)
			return
		}
	}

	// If the client is not in a game, restrict commands
	if client.GetRoomID() == "" && message.Type != SetName && message.Type != GetGames && message.Type != CreateRoom {
		errorMessage.Data = "You must be in a game to perform this action"
		client.Send(errorMessage)
		return
	}

	// If the client is in a game, restrict non-game related actions
	if client.GetRoomID() != "" && message.Type != MovePaddle && message.Type != JoinRoom && message.Type != CreateRoom {
		errorMessage.Data = "You cannot perform this action while in a game"
		client.Send(errorMessage)
		return
	}

	// Process the message based on its type
	switch message.Type {
	case SetName:
		client.HandleSetName(message.Data.(string))
	case GetGames:
		client.HandleGetGames()
	case JoinRoom:
		client.HandleJoinRoom(message.Data.(string))
	case CreateRoom:
		client.HandleCreateRoom()
	case MovePaddle:
		if direction, ok := message.Data.(string); ok {
			switch direction {
			case "up":
				client.HandleMovePaddle(game.Up)
			case "down":
				client.HandleMovePaddle(game.Down)
			default:
				errorMessage.Data = "Invalid move_paddle direction"
				client.Send(errorMessage)
				return
			}
		} else {
			errorMessage.Data = "Invalid move_paddle data"
			client.Send(errorMessage)
			return
		}
	default:
		log.Println("Unknown message type:", message.Type)
	}
}
