package game

type State int

const (
	Waiting State = iota
	Playing
	Paused
	GameOver
)

var stateName = map[State]string{
	Waiting:  "waiting",
	Playing:  "playing",
	Paused:   "paused",
	GameOver: "game_over",
}

func (s State) String() string {
	return stateName[s]
}
