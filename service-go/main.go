package main

import (
	"fmt"
	"net/http"
	"time"
)

func main() {
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintf(w, "Hello from Go! Time: %s", time.Now())
	})
	fmt.Println("Server starting on port 8080...")
	http.ListenAndServe(":8080", nil)

}