package server

import (
	"github.com/stretchr/testify/assert"
	"pingpong/game"
	"pingpong/protocol"
	"testing"
)

// TestClientNameNotSet tests the scenario where the client's name is not set.
func TestClientNameNotSet(t *testing.T) {
	StartTestServer()

	conn := ConnectToServer(t)
	defer conn.Close()

	SendMessage(t, conn, protocol.Message{
		Type: protocol.GetGames,
	})

	response := ReadMessage(t, conn)

	expectedMessage := protocol.Message{
		Type: protocol.Error,
		Data: "Name must be set first",
	}
	assert.Equal(t, expectedMessage, response)
}

// TestClientNotInGame tests the scenario where the client is not in a game.
func TestClientNotInGame(t *testing.T) {
	StartTestServer()

	conn := ConnectToServer(t)
	defer conn.Close()

	SendMessage(t, conn, protocol.Message{
		Type: protocol.SetName,
		Data: "Player1",
	})

	SendMessage(t, conn, protocol.Message{
		Type: protocol.MovePaddle,
		Data: game.Up,
	})

	response := ReadMessage(t, conn)

	expectedMessage := protocol.Message{
		Type: protocol.Error,
		Data: "You must be in a game to perform this action",
	}
	assert.Equal(t, expectedMessage, response)
}

// TestClientInGameCannotPerformNonGameActions tests the scenario where the client is in a game
// and attempts to perform non-game actions like "set_name" or "get_games".
func TestClientInGameCannotPerformNonGameActions(t *testing.T) {
	StartTestServer()

	conn := ConnectToServer(t)
	defer conn.Close()

	SendMessage(t, conn, protocol.Message{
		Type: protocol.SetName,
		Data: "Player1",
	})

	createRoomMessage := protocol.Message{
		Type: protocol.CreateRoom,
	}
	SendMessage(t, conn, createRoomMessage)

	getGamesMessage := protocol.Message{
		Type: protocol.GetGames,
	}
	SendMessage(t, conn, getGamesMessage)

	response := ReadMessage(t, conn, "create_room_response")
	expectedMessage := protocol.Message{
		Type: protocol.Error,
		Data: "You cannot perform this action while in a game",
	}
	assert.Equal(t, expectedMessage, response)

	setNameAgainMessage := protocol.Message{
		Type: protocol.SetName,
		Data: "Player2",
	}
	SendMessage(t, conn, setNameAgainMessage)

	response = ReadMessage(t, conn, "create_room_response")
	expectedMessage = protocol.Message{
		Type: protocol.Error,
		Data: "You cannot perform this action while in a game",
	}
	assert.Equal(t, expectedMessage, response)
}

// TestClientCanMovePaddleInGame tests that the client can still perform game-related actions like "move_paddle" when in a game.
func TestClientCanMovePaddleInGame(t *testing.T) {
	StartTestServer()

	conn := ConnectToServer(t)
	defer conn.Close()

	SendMessage(t, conn, protocol.Message{
		Type: protocol.SetName,
		Data: "Player1",
	})

	SendMessage(t, conn, protocol.Message{
		Type: protocol.CreateRoom,
	})

	SendMessage(t, conn, protocol.Message{
		Type: protocol.MovePaddle,
		Data: "up",
	})

	response := ReadMessage(t, conn, "create_room_response")
	expectedMessage := protocol.Message{
		Type: protocol.MovePaddleResponse,
		Data: "up",
	}
	assert.Equal(t, expectedMessage, response)
}

// TestMissingNameData tests the scenario where the client tries to set their name but doesn't provide any data.
func TestMissingNameData(t *testing.T) {
	StartTestServer()

	conn := ConnectToServer(t)
	defer conn.Close()

	SendMessage(t, conn, protocol.Message{
		Type: protocol.SetName,
		Data: "",
	})

	response := ReadMessage(t, conn)

	expectedMessage := protocol.Message{
		Type: protocol.Error,
		Data: "Name cannot be empty",
	}
	assert.Equal(t, expectedMessage, response)
}

// TestInvalidPaddleMoveData tests the scenario where the client sends invalid data for the "move_paddle" action.
func TestInvalidPaddleMoveData(t *testing.T) {
	StartTestServer()

	conn := ConnectToServer(t)
	defer conn.Close()

	SendMessage(t, conn, protocol.Message{
		Type: protocol.SetName,
		Data: "Player1",
	})

	SendMessage(t, conn, protocol.Message{
		Type: protocol.CreateRoom,
	})

	SendMessage(t, conn, protocol.Message{
		Type: protocol.MovePaddle,
		Data: 123, // Invalid data type (should be a string)
	})

	response := ReadMessage(t, conn, "create_room_response")
	expectedMessage := protocol.Message{
		Type: protocol.Error,
		Data: "Invalid move_paddle data",
	}
	assert.Equal(t, expectedMessage, response)
}
