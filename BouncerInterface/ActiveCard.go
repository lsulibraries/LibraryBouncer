// opens a web browser to a specific page

package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"os"
	"os/exec"
	"runtime"
	"time"

	"github.com/gookit/color"
)

type userinfo struct {
	Expiration string `json:"expiration"`
	Name       string `json:"user"`
}

func QueryAPI(uid string) userinfo {
	url := "http://libguardshack.lsu.edu/expiration/?id=" + uid
	resp, err := http.Get(url)
	defer resp.Body.Close()
	if err != nil {
		fmt.Fprintf(os.Stderr, "fetch: %v\n", err)
		return userinfo{}
	}
	b, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fetch: reading %s: %v\n", url, err)
		return userinfo{}
	}
	user := userinfo{}
	jsonErr := json.Unmarshal(b, &user)
	if jsonErr != nil {
		fmt.Println(jsonErr)
		return userinfo{}
	}
	return user
}

func isExpired(user userinfo) bool {
	exp, err := time.Parse("2006-01-02", user.Expiration)
	if err != nil {
		fmt.Println(err)
		return true
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

func Clear() {
	var c *exec.Cmd
	var doClear = true
	switch runtime.GOOS {
	case "darwin":
	case "linux":
		c = exec.Command("clear")
	case "windows":
		c = exec.Command("cmd", "/c", "cls")
	default:
		doClear = false
	}
	if doClear {
		c.Stdout = os.Stdout
		c.Run()
	}
}

func printScreen(info string, status string) {
	Clear()
	color.Yellow.Println("\n*********************")
	color.Yellow.Println("Welcome to ActiveCard")
	color.Yellow.Println("*********************")
	color.Cyan.Println("\nScan a Tigercard, we'll check if the account is active.")
	color.Gray.Println("\n(If you lose connection, try clicking on this display window and rescanning.)")
	if status == "ok" {
		color.Cyan.Printf("\n%s\n", info)
	} else if status == "not ok" {
		color.Red.Printf("\n%s\n", info)
	}
}

func main() {
	printScreen("", "none")
	for {
		input := scanStdin()
		if input != "" {
			user := QueryAPI(input)
			expired := isExpired(user)
			if expired {
				printScreen("Not authorized patron: "+user.Name, "not ok")
			} else {
				printScreen("authorized patron: "+user.Name, "ok")
			}
		}
	}
}
