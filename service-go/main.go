package main

import (
	"fmt"
	"net/http"
	"time"
)

// HelloHandler handles the root endpoint
func HelloHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "Hello from Go! Time: %s", time.Now())
}

func main() {
	http.HandleFunc("/", HelloHandler)
	fmt.Println("Server starting on port 8080...")
	http.ListenAndServe(":8080", nil)
}