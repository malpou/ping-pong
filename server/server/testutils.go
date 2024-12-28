package server

import (
	"encoding/json"
	"github.com/gorilla/websocket"
	"net/http"
	"pingpong/protocol"
	"sync"
	"testing"
	"time"
)

var (
	testServer *Server
	serverOnce sync.Once
	serverAddr = "ws://localhost:8080/"
)

// StartTestServer starts the WebSocket server only once.
func StartTestServer() {
	serverOnce.Do(func() {
		testServer = NewServer()
		go func() {
			http.HandleFunc("/", testServer.HandleConnection) // WebSocket server at root path
			if err := http.ListenAndServe(":8080", nil); err != nil {
				panic("Server failed to start: " + err.Error())
			}
		}()
		// Wait for the server to start
		time.Sleep(100 * time.Millisecond)
	})
}

// ConnectToServer creates a WebSocket connection to the test server.
func ConnectToServer(t *testing.T) *websocket.Conn {
	conn, _, err := websocket.DefaultDialer.Dial(serverAddr, nil)
	if err != nil {
		t.Fatal("Failed to connect to WebSocket server:", err)
	}
	return conn
}

// SendMessage sends a Message over the WebSocket connection.
func SendMessage(t *testing.T, conn *websocket.Conn, msg protocol.Message) {
	data, err := json.Marshal(msg)
	if err != nil {
		t.Fatal("Failed to marshal message:", err)
	}
	err = conn.WriteMessage(websocket.TextMessage, data)
	if err != nil {
		t.Fatal("Failed to send message:", err)
	}
}

// ReadMessage reads a Message from the WebSocket connection with a 1-second timeout.
// Optionally, it can ignore messages of specified types.
func ReadMessage(t *testing.T, conn *websocket.Conn, ignoreTypes ...string) protocol.Message {
	// Create a channel to receive the message
	messageChannel := make(chan []byte, 1)
	errorChannel := make(chan error, 1)

	// Start a goroutine to read the message
	go func() {
		_, message, err := conn.ReadMessage()
		if err != nil {
			errorChannel <- err
			return
		}
		messageChannel <- message
	}()

	// Wait for the message or timeout
	select {
	case message := <-messageChannel:
		// Unmarshal the message into the protocol.Message struct
		var msg protocol.Message
		err := json.Unmarshal(message, &msg)
		if err != nil {
			t.Fatal("Failed to unmarshal message:", err)
		}

		// Check if the message type is in the list of types to ignore
		for _, ignoreType := range ignoreTypes {
			if msg.Type == ignoreType {
				// If the message is to be ignored, recursively call ReadMessage to read the next message
				return ReadMessage(t, conn, ignoreTypes...)
			}
		}

		// Return the relevant message
		return msg

	case err := <-errorChannel:
		t.Fatal("Failed to read message from WebSocket:", err)
	case <-time.After(1 * time.Second):
		t.Fatal("Read message timed out after 1 second")
	}

	// Return a zero value to avoid a compiler error; this won't be reached due to the t.Fatal calls
	return protocol.Message{}
}
