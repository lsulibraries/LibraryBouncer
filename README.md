# LibraryBouncer
scan a TigerCard to check a patron's library permissions

### Two Programs

#### BouncerAPI

- a secure server running within our local network (not available to the internet)
- accepts a url in the form http://libguardshack.lsu.edu/expiration/?id=1234567890123456

  - where the number is a Tigercard id

- returns a json response with that person's Symphony expiration date

  - {"expiration": "yyyy-mm-dd"}

- logs

  - only non-personally identifiable info
  - ./BouncerAPI/access_stats.txt

- big picture:

  - The challenge is to log in and gather info from the Symphony server
  - while protecting the Symphony login passwords and other secrets.
  - If we store those secrets on a public computer, then a bad actor can hack our Symphony database.
  - So we create a tiny server within the library IT stack
  - that stores the secrets in a safe place and
  - only shares to the world info that is not secret.
  - specifically, it publicly shares only whether a given library userid is expired.  
  - So, while the server's port is accessible to anyone inside the lsu network, it only returns info we are comfortable sharing to everyone (including bad actors).
  - Later we will talk about an interface program that queries this server.

- what is the server:

  - the entire webapp is coded in the app.py file.
  - it's a very minimal Apache/mod_wsgi/flask server
  - it accepts a request with an ?id= value, and return a response: {"expiration": "some date info"}.
  - BouncerInterface requires this exact json response, so be careful if you modify the server's json response.
  - the internal logs hold richer data.  During this logging, it temporarily knows the individual's id, in order to look up Degree/School/College.  After the lookup, it forgets all identifiably info.
  - these logs can be parsed to make sense of the who uses the library at different times.  (As of date, the requirements of this parser are unspecified.)

- to revise the server:

  - the entire server is coded in the app.py file.
  - it's a very minimal Flask server (python3)
  - Note: if you add elements to the server json response, be sure to add a matching element to the ActiveStudent.go program.  Go is very strict about types.

- to build a dev instance:

  - follow the instructions at gnatty repo to install docker and github
  - clone this github repository
  - cd into the APIserver directory
  - touch a file at ./BouncerAPI/access_stats.txt  (making this empty file is a necessary hack)
  - create a file at ./BouncerAPI/user_pass.json with the text {"user": "JoeShmoe", "password": "JoesPassword"} matching a Sirsi Workflows admin user
  - ```docker-compose up --build -d```
  - the webserver will be available at url localhost:8000
  - in the docker-compose.yml file is a line "ports: 8000:80" where 8000 is the outside visible port and 80 is the port inside the container
  - you may start and stop the API server with ```docker-compose up -d``` and ```docker-compose stop```
  - the docker constainers & the flask server will restart on failure, unless you ```docker-compose stop```
  - it will log flask error in access_stats.txt
  - it logs container-level errors in ```docker-compose logs```
  - ```docker-compose down``` will kill the containers and wipe the user/pass

- to build a production instance:

  - with CentOS 7
  - ```sudo yum install httpd python3 mod_wsgi python3-devel
  - sudo pip3 install flask requests
  - cd /var/www/
  - sudo git clone https://github.com/lsulibraries/LibraryBouncer
  - copy or symlink /var/www/LibraryBouncer/config/apache/librarybouncer.conf to /etc/httpd/conf.d/librarybouncer.conf
  - create a file at ./BouncerAPI/user_pass.json with permissions -rw-------
  - create a file at ./BouncerAPI/access_stats.txt
  - sudo chown -R garmstrong:apache /var/www/LibraryBouncer
  - sudo firewall-cmd --zone=public --permanent --add-service=http
  - sudo firewall-cmd --zone=public --permanent --add-service=https
  - sudo systemctl restart httpd```
  - disable selinux unless you want to figure out that madness
  - look in the apache logs & the access_stats.txt for error messages

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

  for example, if you move the APIserver url, you'll need to update the hardcoded address in ActiveCard.go

  - install Golang on your computer
  - cd to ./BouncerInterface/ in your terminal
  - ```go get github.com/gookit/color```
  - edit ActiveCard.go
  - for Windows: ```go build ActiveCard.go```
  - for linux: ```GOOS=windows GOARCH=amd64 go build ActiveCard.go```
  - the new ActiveCard.exe file in ./BouncerInterface folder is a windows executable.
  - replace the ActiveCard.exe file on the front desk Windows computer's Desktop with this new version

