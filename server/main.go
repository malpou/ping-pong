package main

import (
	"log"
	"net/http"
	"pingpong/server"
)

func main() {
	s := server.NewServer()
	http.HandleFunc("/", s.HandleConnection)
	log.Println("Server started on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
