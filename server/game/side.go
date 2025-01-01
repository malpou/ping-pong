package game

type Side int

const (
	Left Side = iota
	Right
	None
)

var sideName = map[Side]string{
	Left:  "left",
	Right: "right",
	None:  "none",
}

func (s Side) String() string {
	return sideName[s]
}
