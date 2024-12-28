package game

import (
	"math"
	"time"
)

type State string
type Side string

const (
	StateWaiting       State = "waiting"
	StatePlaying       State = "playing"
	StatePaused        State = "paused"
	StateGameOver      State = "game_over"
	SideLeft           Side  = "left"
	SideRight          Side  = "right"
	PaddleUp                 = 'U'
	PaddleDown               = 'D'
	PointsToWin              = 5
	Size                     = 1.0
	ScoreDelay               = 1.0
	StartDelay               = 3.0
	BaseSpeed                = 1.0 / 60.0 / 2.0
	SpeedTier1               = 1.25
	SpeedTier2               = 1.5
	SpeedIncrement           = 0.1
	MaxSpeedMultiplier       = 3.0
)

type Game struct {
	LeftPaddle  *Paddle
	RightPaddle *Paddle
	Ball        *Ball
	LeftScore   int
	RightScore  int
	Winner      string
	State       State
	PlayerCount int
	BallTowards Side
	ScoreTimer  time.Time
	StartTimer  time.Time
	ScoringSide Side
	PaddleHits  int
	Starting    bool
}

func NewGame() *Game {
	return &Game{
		LeftPaddle:  NewPaddle(0.05),
		RightPaddle: NewPaddle(0.95),
		Ball:        NewBall(),
		State:       StateWaiting,
	}
}

func (g *Game) Update() {
	if g.Winner != "" || g.State != StatePlaying || g.PlayerCount < 2 {
		return
	}

	if g.Starting {
		if time.Since(g.StartTimer).Seconds() >= StartDelay {
			g.Starting = false
			g.Ball.Reset(SideLeft)
		}
		return
	}

	if g.ScoringSide != "" {
		if time.Since(g.ScoreTimer).Seconds() >= ScoreDelay {
			g.Ball.Reset(g.ScoringSide)
			g.ScoringSide = ""
		}
		return
	}

	g.Ball.UpdatePosition()

	if g.Ball.X <= 0 {
		g.HandleScoring(SideLeft, g.RightScore+1)
	} else if g.Ball.X >= Size {
		g.HandleScoring(SideRight, g.LeftScore+1)
	}

	g.BallTowards = g.DetermineBallTowards()

	if g.LeftPaddle.IsOnPaddle(g.Ball) && g.BallTowards == SideLeft {
		g.HandlePaddleHit(g.LeftPaddle)
	}
	if g.RightPaddle.IsOnPaddle(g.Ball) && g.BallTowards == SideRight {
		g.HandlePaddleHit(g.RightPaddle)
	}
}

func (g *Game) DetermineBallTowards() Side {
	angleMod := math.Mod(g.Ball.Angle, 2*math.Pi)
	if math.Pi/2 <= angleMod && angleMod <= 3*math.Pi/2 {
		return SideLeft
	}
	return SideRight
}

func (g *Game) HandleScoring(side Side, newScore int) {
	if side == SideLeft {
		g.RightScore = newScore
	} else {
		g.LeftScore = newScore
	}
	g.PaddleHits = 0
	g.Ball.SetSpeed(BaseSpeed)
	g.ResetPaddles()
	g.ScoreTimer = time.Now()
	g.ScoringSide = side
	g.CheckWinner()
}

func (g *Game) CheckWinner() {
	if g.LeftScore >= PointsToWin {
		g.Winner = "left"
		g.State = StateGameOver
	} else if g.RightScore >= PointsToWin {
		g.Winner = "right"
		g.State = StateGameOver
	}
}

func (g *Game) MovePaddle(playerName string, direction byte) {
	switch playerName {
	case "left":
		if direction == PaddleUp {
			g.LeftPaddle.MoveUp()
		} else if direction == PaddleDown {
			g.LeftPaddle.MoveDown()
		}
	case "right":
		if direction == PaddleUp {
			g.RightPaddle.MoveUp()
		} else if direction == PaddleDown {
			g.RightPaddle.MoveDown()
		}
	}
}

func (g *Game) ResetPaddles() {
	g.LeftPaddle.ResetPosition()
	g.RightPaddle.ResetPosition()
}

func (g *Game) HandlePaddleHit(paddle *Paddle) {
	g.PaddleHits++
	g.Ball.SetSpeed(g.CalculateBallSpeed())
	g.Ball.Angle = g.CalcAngle(paddle)
}

func (g *Game) CalcAngle(paddle *Paddle) float64 {
	var angleMin, angleMax float64
	if g.BallTowards == SideLeft {
		angleMin, angleMax = -math.Pi/3, math.Pi/3
	} else {
		angleMin, angleMax = 4*math.Pi/3, 2*math.Pi/3
	}
	relativeY := (g.Ball.Y - paddle.YMin()) / (paddle.YMax() - paddle.YMin())
	return angleMin + relativeY*(angleMax-angleMin)
}

func (g *Game) CalculateBallSpeed() float64 {
	if g.PaddleHits < 5 {
		return BaseSpeed
	} else if g.PaddleHits < 10 {
		return BaseSpeed * SpeedTier1
	} else if g.PaddleHits < 20 {
		multiplier := SpeedTier2 + float64(g.PaddleHits-10)*SpeedIncrement
		return BaseSpeed * math.Min(multiplier, MaxSpeedMultiplier)
	}
	return BaseSpeed * MaxSpeedMultiplier
}

func (g *Game) AddPlayer() {
	g.PlayerCount++
	if g.PlayerCount == 2 {
		g.State = StatePlaying
		g.Starting = true
		g.StartTimer = time.Now()
	}
}

func (g *Game) RemovePlayer() {
	g.PlayerCount--
	if g.PlayerCount < 2 && g.State == StatePlaying {
		g.State = StatePaused
	}
}
