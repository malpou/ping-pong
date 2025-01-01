package game

import (
	"math"
	"math/rand"
)

type Ball struct {
	X          float64
	Y          float64
	Angle      float64
	Speed      float64
	Radius     float64
	FirstServe bool
}

func NewBall() *Ball {
	return &Ball{
		X:          0.5,
		Y:          0.5,
		Radius:     0.02,
		FirstServe: true,
		Speed:      BaseSpeed,
	}
}

func (b *Ball) SetSpeed(newSpeed float64) {
	b.Speed = newSpeed
}

func (b *Ball) UpdatePosition() {
	vX := b.Speed * math.Cos(b.Angle)
	vY := b.Speed * math.Sin(b.Angle)

	b.X += vX
	b.Y += vY

	// Bounce off top and bottom walls
	if (b.Y <= b.Radius && math.Pi <= math.Mod(b.Angle, 2*math.Pi) && math.Mod(b.Angle, 2*math.Pi) <= 2*math.Pi) ||
		(b.Y >= 1-b.Radius && 0 <= math.Mod(b.Angle, 2*math.Pi) && math.Mod(b.Angle, 2*math.Pi) <= math.Pi) {
		b.Angle = -b.Angle
	}
}

func (b *Ball) SetDirection(direction Side) {
	if direction == Left {
		b.Angle = math.Pi // Towards left
	} else if direction == Right {
		b.Angle = 0 // Towards right
	} else {
		// Random first serve
		if rand.Intn(2) == 0 {
			b.Angle = 0
		} else {
			b.Angle = math.Pi
		}
	}
}

func (b *Ball) Reset(direction Side) {
	b.X = 0.5
	b.Y = 0.5
	b.FirstServe = false

	if direction == Left || direction == Right {
		b.SetDirection(direction)
	} else {
		// Handle the case for random first serve if needed
		b.SetDirection(None)
	}
}
