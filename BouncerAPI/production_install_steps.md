Production server setup:

  - Centos8
  - sudo yum install httpd python3 mod_wsgi
  - sudo pip3 install flask requests

  - create this folder tree:

/var/www/ActiveCard/
  -rw--------. garmstrong apache   user_pass.json
  drwrxr-xr-x. garmstrong apache   app/

/var/www/ActiveCard/app/
  -rw-rw-r--. garmstrong apache    access_stats.json
  -rw-rw-r--. garmstrong apache    app.py
  -rw-rw-r--. garmstrong apache    wsgi.py


/var/www/ActiveCard/app/wsgi.py

```
#! /usr/bin/python3

from app import application

if __name__ == "__main__":
    application.run()
```


/var/httpd/conf.d/activecard.conf :
```
  <VirtualHost *>
    ServerName libguardshack.lsu.edu
    WSGIDaemonProcess application user=garmstrong group=apache threads=2 home=/var/www/ActiveCard/app
    WSGIScriptAlias /activecard /var/www/ActiveCard/app/wsgi.py
    <Directory /var/www/ActiveCard/app/>
        WSGIProcessGroup application
        WSGIApplicationGroup %{GLOBAL}
        Order deny,allow
        Allow from all
    </Directory>
</VirtualHost>
```