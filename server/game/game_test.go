package game

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestNewGame(t *testing.T) {
	game := NewGame()

	assert.NotNil(t, game.LeftPaddle, "Left paddle should be initialized")
	assert.NotNil(t, game.RightPaddle, "Right paddle should be initialized")
	assert.NotNil(t, game.Ball, "Ball should be initialized")
	assert.Equal(t, Waiting, game.State, "Initial game state should be 'waiting'")
	assert.Equal(t, 0, game.LeftScore, "Initial left score should be 0")
	assert.Equal(t, 0, game.RightScore, "Initial right score should be 0")
}

func TestAddPlayer(t *testing.T) {
	game := NewGame()

	game.AddPlayer()
	assert.Equal(t, 1, game.PlayerCount, "Player count should increase to 1")
	assert.Equal(t, Waiting, game.State, "Game state should remain 'waiting' with 1 player")

	game.AddPlayer()
	assert.Equal(t, 2, game.PlayerCount, "Player count should increase to 2")
	assert.Equal(t, Playing, game.State, "Game state should change to 'playing' with 2 players")
	assert.True(t, game.Starting, "Game should be in starting state after adding the second player")
}

func TestRemovePlayer(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()

	game.RemovePlayer()
	assert.Equal(t, 1, game.PlayerCount, "Player count should decrease to 1")
	assert.Equal(t, Paused, game.State, "Game state should change to 'paused' when player count drops below 2")
}

func TestGameStartTimer(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()

	assert.True(t, game.Starting, "Game should be in starting state")

	time.Sleep(StartDelay * time.Second)
	game.Update()

	assert.False(t, game.Starting, "Game should no longer be in starting state after delay")
}

func TestMovePaddle(t *testing.T) {
	game := NewGame()

	initialLeftY := game.LeftPaddle.Y
	initialRightY := game.RightPaddle.Y

	game.MovePaddle(Left, Up)
	assert.Less(t, game.LeftPaddle.Y, initialLeftY, "Left paddle should move up")

	game.MovePaddle(Right, Down)
	assert.Greater(t, game.RightPaddle.Y, initialRightY, "Right paddle should move down")
}

func TestHandleScoring(t *testing.T) {
	game := NewGame()

	game.HandleScoring(Left, 1)
	assert.Equal(t, 1, game.RightScore, "Right score should increase when scoring on the left side")
	assert.Equal(t, Left, game.ScoringSide, "Scoring side should be set to the side that scored")

	// Simulate the delay and update
	time.Sleep(ScoreDelay * time.Second)
	game.Update()
	assert.Equal(t, "", game.ScoringSide, "Scoring side should reset after score delay")

	game.HandleScoring(Right, 1)
	assert.Equal(t, 1, game.LeftScore, "Left score should increase when scoring on the right side")
	assert.Equal(t, Right, game.ScoringSide, "Scoring side should be set to the side that scored")

	// Simulate the delay and update
	time.Sleep(ScoreDelay * time.Second)
	game.Update()
	assert.Equal(t, "", game.ScoringSide, "Scoring side should reset after score delay")
}

func TestCheckWinner(t *testing.T) {
	game := NewGame()

	game.LeftScore = PointsToWin
	game.CheckWinner()
	assert.Equal(t, "left", game.Winner, "Left player should be declared winner")
	assert.Equal(t, GameOver, game.State, "Game state should be 'game_over' when a player wins")

	game = NewGame()
	game.RightScore = PointsToWin
	game.CheckWinner()
	assert.Equal(t, "right", game.Winner, "Right player should be declared winner")
	assert.Equal(t, GameOver, game.State, "Game state should be 'game_over' when a player wins")
}

func TestBallCollisionWithPaddles(t *testing.T) {
	game := NewGame()

	// Ball hitting the left paddle
	game.Ball.X = game.LeftPaddle.X + game.Ball.Radius
	game.Ball.Y = game.LeftPaddle.Y
	game.BallTowards = Left
	game.HandlePaddleHit(game.LeftPaddle)

	assert.Greater(t, game.Ball.Speed, BaseSpeed, "Ball speed should increase after hitting paddle")
	assert.Equal(t, 1, game.PaddleHits, "Paddle hits should increase after hitting paddle")

	// Ball hitting the right paddle
	game.Ball.X = game.RightPaddle.X - game.Ball.Radius
	game.Ball.Y = game.RightPaddle.Y
	game.BallTowards = Right
	game.HandlePaddleHit(game.RightPaddle)

	assert.Greater(t, game.Ball.Speed, BaseSpeed, "Ball speed should increase after hitting paddle")
	assert.Equal(t, 2, game.PaddleHits, "Paddle hits should increase after hitting paddle")
}

func TestResetPaddles(t *testing.T) {
	game := NewGame()

	game.LeftPaddle.Y = 0.2
	game.RightPaddle.Y = 0.8
	game.ResetPaddles()

	assert.Equal(t, 0.5, game.LeftPaddle.Y, "Left paddle position should reset to 0.5")
	assert.Equal(t, 0.5, game.RightPaddle.Y, "Right paddle position should reset to 0.5")
}

func TestCalculateBallSpeed(t *testing.T) {
	game := NewGame()

	game.PaddleHits = 4
	assert.Equal(t, BaseSpeed, game.CalculateBallSpeed(), "Ball speed should be base speed for less than 5 hits")

	game.PaddleHits = 7
	assert.Equal(t, BaseSpeed*SpeedTier1, game.CalculateBallSpeed(), "Ball speed should be tier 1 speed for 5-10 hits")

	game.PaddleHits = 15
	expectedSpeed := BaseSpeed * (SpeedTier2 + 5*SpeedIncrement)
	assert.Equal(t, expectedSpeed, game.CalculateBallSpeed(), "Ball speed should increase linearly for 10-20 hits")

	game.PaddleHits = 25
	assert.Equal(t, BaseSpeed*MaxSpeedMultiplier, game.CalculateBallSpeed(), "Ball speed should cap at max speed multiplier after 20 hits")
}

func TestBallMovementAndPaddleCollision(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()
	game.StartTimer = time.Now().Add(-StartDelay * time.Second)
	game.Update()
	game.PaddleHits = 4

	// Simulate ball moving towards the left paddle
	game.Ball.X = game.LeftPaddle.X + game.Ball.Radius
	game.Ball.Y = (game.LeftPaddle.YMin() + game.LeftPaddle.YMax()) / 2
	game.BallTowards = Left

	initialSpeed := game.Ball.Speed
	game.Update()

	assert.Greater(t, game.Ball.Speed, initialSpeed, "Ball speed should increase after hitting the paddle")
	assert.Equal(t, 5, game.PaddleHits, "Paddle hits should increase after collision")
}

func TestScoringViaUpdate(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()
	game.StartTimer = time.Now().Add(-StartDelay * time.Second)

	for game.Starting {
		game.Update()
		time.Sleep(10 * time.Millisecond) // Small delay to simulate game loop
	}

	// Simulate ball crossing the left boundary
	game.Ball.X = -0.1
	game.Update()

	assert.Equal(t, 1, game.RightScore, "Right score should increase when ball crosses the left boundary")
}

func TestPaddleMovementViaUpdate(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()
	game.LeftPaddle.MoveUp()
	game.Update()

	assert.Less(t, game.LeftPaddle.Y, 0.5, "Left paddle should move up after MoveUp is called")
}

func TestGameOverViaUpdate(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()
	game.RightScore = PointsToWin - 1
	game.Ball.X = -0.1 // Simulate scoring for the right player

	game.Update()
	game.Update()

	assert.Equal(t, PointsToWin, game.RightScore, "Right score should reach points to win")
	assert.Equal(t, "right", game.Winner, "Right player should be declared winner")
	assert.Equal(t, GameOver, game.State, "Game state should be 'game_over'")
}

func TestContinuousUpdates(t *testing.T) {
	game := NewGame()
	game.AddPlayer()
	game.AddPlayer()
	game.StartTimer = time.Now().Add(-StartDelay * time.Second)
	game.Update()

	for i := 0; i < 5; i++ {
		game.Update()
	}

	assert.NotEqual(t, 0.5, game.Ball.X, "Ball position should change after multiple updates")
}
