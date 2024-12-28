package game

import (
	"github.com/stretchr/testify/assert"
	"testing"
)

func TestNewPaddle(t *testing.T) {
	// Create a new paddle
	paddle := NewPaddle(0.1)

	// Test the initial properties of the paddle
	assert.Equal(t, 0.1, paddle.X, "X should be set to the provided value")
	assert.Equal(t, 0.5, paddle.Y, "Y should be set to 0.5 by default")
	assert.Equal(t, 0.2, paddle.Height, "Height should be set to 0.2 by default")
	assert.Equal(t, 0.02, paddle.Width, "Width should be set to 0.02 by default")
	assert.Equal(t, 0.01, paddle.Speed, "Speed should be set to 0.01 by default")

	// Test YMin and YMax
	expectedYMin := paddle.Y - paddle.Height/2
	assert.Equal(t, expectedYMin, paddle.YMin(), "YMin should return the correct minimum Y position")

	expectedYMax := paddle.Y + paddle.Height/2
	assert.Equal(t, expectedYMax, paddle.YMax(), "YMax should return the correct maximum Y position")
}

func TestIsOnPaddle(t *testing.T) {
	paddle := NewPaddle(0.1)

	ball := NewBall()
	ball.X = 0.1 // Set the ball's X position to match the paddle
	ball.Y = 0.5 // Set the ball's Y position to match the paddle

	assert.True(t, paddle.IsOnPaddle(ball), "Ball should be on the paddle")

	ball.Y = 0.8
	assert.False(t, paddle.IsOnPaddle(ball), "Ball should not be on the paddle after moving off")
}

func TestMoveUp(t *testing.T) {
	paddle := NewPaddle(0.1)

	// Test initial position
	initialY := paddle.Y

	// Move the paddle up once
	paddle.MoveUp()
	assert.Equal(t, initialY-paddle.Speed, paddle.Y, "Paddle Y should decrease by Speed when moving up")

	// Move the paddle up multiple times to check it doesn't go below the minimum limit
	for i := 0; i < 100; i++ {
		paddle.MoveUp()
	}
	// Ensure the Y doesn't go below the minimum limit
	assert.Equal(t, paddle.Height/2, paddle.Y, "Paddle Y should not go below the minimum limit after multiple moves")
}
func TestMoveDown(t *testing.T) {
	// Create a paddle
	paddle := NewPaddle(0.1)

	// Test initial position
	initialY := paddle.Y

	// Move the paddle down once
	paddle.MoveDown()
	assert.Equal(t, initialY+paddle.Speed, paddle.Y, "Paddle Y should increase by Speed when moving down")

	for i := 0; i < 100; i++ {
		paddle.MoveDown()
	}
	assert.Equal(t, 1.0-paddle.Height/2, paddle.Y, "Paddle Y should not go above the maximum limit after multiple moves")
}

func TestReset(t *testing.T) {
	paddle := NewPaddle(0.1)

	paddle.Y = 0.8
	paddle.ResetPosition()

	assert.Equal(t, 0.5, paddle.Y, "Paddle Y should be reset to 0.5")
}
