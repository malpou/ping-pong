package game

import (
	"github.com/stretchr/testify/assert"
	"math"
	"testing"
)

func TestNewBall(t *testing.T) {
	ball := NewBall()

	assert.Equal(t, 0.5, ball.X, "X position should be set to 0.5 by default")
	assert.Equal(t, 0.5, ball.Y, "Y position should be set to 0.5 by default")
	assert.Equal(t, 0.02, ball.Radius, "Radius should be set to 0.02 by default")
	assert.Equal(t, true, ball.FirstServe, "FirstServe should be true by default")
	assert.Equal(t, BaseSpeed, ball.Speed, "Speed should be set to the default BaseSpeed")
}

func TestBallSetSpeed(t *testing.T) {
	ball := NewBall()

	ball.SetSpeed(0.05)

	assert.Equal(t, 0.05, ball.Speed, "Ball speed should be updated to the new value")
}

func TestBallUpdatePosition(t *testing.T) {
	ball := NewBall()

	ball.Angle = math.Pi / 4

	initialX := ball.X
	initialY := ball.Y

	ball.UpdatePosition()

	assert.NotEqual(t, initialX, ball.X, "X position should change after updating position")
	assert.NotEqual(t, initialY, ball.Y, "Y position should change after updating position")
}
func TestBallBounceOffTopWall(t *testing.T) {
	ball := NewBall()

	// Set the ball's position near the top wall
	ball.Y = ball.Radius + 0.01
	ball.Angle = math.Pi / 4 // Moving towards the top wall

	ball.UpdatePosition()

	assert.Equal(t, math.Pi/4, ball.Angle, "Ball should bounce off the top wall")
}

func TestBallBounceOffBottomWall(t *testing.T) {
	ball := NewBall()

	// Set the ball's position near the bottom wall
	ball.Y = 1 - ball.Radius - 0.01
	ball.Angle = 3 * math.Pi / 4 // Moving towards the bottom wall

	ball.UpdatePosition()

	assert.Equal(t, 3*math.Pi/4, ball.Angle, "Ball should bounce off the bottom wall")
}

func TestBallSetDirection(t *testing.T) {
	ball := NewBall()

	ball.SetDirection(Left)
	assert.Equal(t, math.Pi, ball.Angle, "Ball angle should be set to Pi when direction is left")

	ball.SetDirection(Right)
	assert.Equal(t, 0.0, ball.Angle, "Ball angle should be set to 0 when direction is right")

	ball.SetDirection("")
	assert.True(t, ball.Angle == 0 || ball.Angle == math.Pi, "Ball angle should be randomly set to 0 or Pi")
}

func TestBallReset(t *testing.T) {
	ball := NewBall()

	ball.SetDirection(Right)
	ball.X = 0.2
	ball.Y = 0.8

	ball.Reset(Left)

	assert.Equal(t, 0.5, ball.X, "Ball X position should be reset to 0.5")
	assert.Equal(t, 0.5, ball.Y, "Ball Y position should be reset to 0.5")

	assert.False(t, ball.FirstServe, "FirstServe should be false after reset")

	assert.Equal(t, math.Pi, ball.Angle, "Ball angle should be set to Pi when resetting to left")
}

func TestBallResetFirstServe(t *testing.T) {
	ball := NewBall()

	assert.True(t, ball.FirstServe, "FirstServe should be true initially")

	ball.Reset(Left)

	assert.False(t, ball.FirstServe, "FirstServe should be false after the first reset")
}
