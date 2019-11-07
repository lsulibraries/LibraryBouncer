// opens a web browser to a specific page

package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"time"
)

type userinfo struct {
	Expiration string `json:"expiration"`
}

func QueryAPI(uid string) userinfo {
	url := "http://localhost:8000/?id=" + uid
	resp, err := http.Get(url)
	defer resp.Body.Close()
	if err != nil {
		fmt.Fprintf(os.Stderr, "fetch: %v\n", err)
		os.Exit(1)
	}
	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fetch: reading %s: %v\n", url, err)
		os.Exit(1)
	}
	user := userinfo{}
	jsonErr := json.Unmarshal(b, &user)
	if jsonErr != nil {
		fmt.Println(jsonErr)
		os.Exit(1)
	}
	return user
}

func isExpired(user userinfo) bool {
	exp, err := time.Parse("2006-01-02", user.Expiration)
	if err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
	if exp.After(time.Now()) {
		return false
	} else {
		return true
	}
}

func scanStdin() string {
	scanner := bufio.NewScanner(os.Stdin)
	for scanner.Scan() {
		return scanner.Text()
	}
	return ""
}

func main() {
	fmt.Println("\n*********************\nWelcome to ActiveCard\n*********************\n\nScan a Tigercard, we'll check if the account is active.\n\n(If you lose connection, try clicking on this display window and rescanning.)\n\n")
	for {
		input := scanStdin()
		if input != "" {
			user := QueryAPI(input)
			expired := isExpired(user)
			if expired {
				fmt.Println("Not authorized patron")
			} else {
				fmt.Println("authorized patron")
			}
		}
	}
}
