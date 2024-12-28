package game

import "math"

type Paddle struct {
	X      float64
	Y      float64
	Height float64
	Width  float64
	Speed  float64
}

func NewPaddle(xPos float64) *Paddle {
	return &Paddle{
		X:      xPos,
		Y:      0.5,
		Height: 0.2,
		Width:  0.02,
		Speed:  0.01,
	}
}

func (p *Paddle) YMin() float64 {
	return p.Y - p.Height/2
}

func (p *Paddle) YMax() float64 {
	return p.Y + p.Height/2
}

func (p *Paddle) IsOnPaddle(ball *Ball) bool {
	if math.Abs(ball.X-p.X) <= ball.Radius+p.Width/2 {
		if p.YMin()-ball.Radius <= ball.Y && ball.Y <= p.YMax()+ball.Radius {
			return true
		}
	}
	return false
}

func (p *Paddle) MoveUp() {
	newY := p.Y - p.Speed
	p.Y = math.Max(p.Height/2, newY)
}

func (p *Paddle) MoveDown() {
	newY := p.Y + p.Speed
	p.Y = math.Min(1.0-p.Height/2, newY)
}

func (p *Paddle) ResetPosition() {
	p.Y = 0.5
}
