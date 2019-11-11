# LibraryBouncer
scan a TigerCard to check a patron's library permissions

### Two Programs

#### BouncerAPI

- a secure server running within our local network (not available to the internet)
- accepts a url in the form {url to server}/?id=1234567890123456

  - where the number is a Tigercard id
  - or an 89 number

- returns a json response with that person's Symphony expiration date

  - {"user": "Last, First Middle", "expiration": "yyyy-mm-dd"}

- big picture:

  - The challenge is to log in and gather info from the Symphony server
  - while protecting the Symphony login passwords and other secrets.
  - If we store those secrets on a public computer, then a bad actor can hack our Symphony database.
  - So we create a tiny server within the library IT stack
  - that stores the secrets in a safe place and
  - only shares to the world info that is not secret.
  - So, while the server's port is accessible to anyone inside the lsu network, it only returns info we are comfortable sharing to everyone (including bad actors).
  - Later we will talk about an interface program that queries this server.

- to build:

  - follow the instructions at gnatty repo to install docker and github
  - clone this github repository
  - cd into the APIserver directory
  - create a file named "user_pass.json"

    - with the text {"user": "JoeShmoe", "password": "MyOfficeIsARiver"}
    - where that user/password can log into Symphony to access Patron info

  - ```docker-compose up --build -d```
  - the webserver will be available at url {local machine url}:8000
  - in the docker-compose.yml file is a line "ports: 8000:80" where 8000 is the outside visible port and 80 is the port inside the container

- to secure:

  - after build, Delete the user_pass.json file
  - the docker server will remember the Symphony user/pass
  - you may start and stop the API server with ```docker-compose up -d``` and ```docker-compose stop```
  - though it will stay up & restart on failure, until you ```docker-compose stop```
  - ```docker-compose down``` will kill the containers and wipe the user/pass

- to revise the server:

  - the entire server is coded in the app.py file.
  - it's a very minimal Flask server (python3)
  - if you add elements to the server json response, be sure to add a matching element to the ActiveStudent.go program


#### BouncerInterface

- A security guard will have a Windows computer with this program running
- They will swipe a TigerCard through a connected card reader
- which will send the user_id to the running ActiveCard program
- the ActiveCard program will query the API server described above and print a line "authorized patron" or "Not authorized patron"
- For the expected errors, a text message will guide the Security Guard toward possible solutions
- This ActiveCard program gives minimal info on the patron & holds no secrets, because it is located in an insecure place


- to run:

  - Click the program icon on the Desktop
  - See the command prompt window that open
  - Keep this window "in focus" when scanning a card

- to edit then build the executable from the source code:

  - for example, if you move the APIserver url, you'll need to update the hardcoded server in ActiveCard.go

  - install Golang on your computer
  - cd to ./BouncerInterface/ in your terminal
  - ```go get github.com/gookit/color```
  - edit ActiveCard.go
  - for Windows: ```go build ActiveCard.go```
  - for linux: ```GOOS=windows GOARCH=amd64 go build ActiveCard.go```
  - the new ActiveCard.exe file in ./BouncerInterface/ is a windows executable.
