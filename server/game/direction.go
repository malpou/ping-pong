package game

type Direction int

const (
	Up Direction = iota
	Down
)

var directionName = map[Direction]string{
	Up:   "up",
	Down: "down",
}

func (d Direction) String() string {
	return directionName[d]
}
