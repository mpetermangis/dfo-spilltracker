
# Spill Tracker

This readme is the installation guide for the DFO Spill Tracker.

## System Requirements

A Linux server (Ubuntu or Debian) with 1GB memory. 

## Installation

First basic setup, install required packages. 

`sudo timedatectl set-timezone America/Vancouver`

Double check:

`sudo timedatectl`

`sudo apt-get update`

`sudo apt-get upgrade`

`sudo apt-get install postgresql nginx git supervisor python-dev python3-pip build-essential apache2-utils fail2ban`

Install python virtualenv:

`sudo pip3 install virtualenv`

Create and activate a python3 virtualenv in your home folder, let's call it 'spill':

`cd ~`

`virtualenv -p python3 spill`

`source ~/spill/bin/activate`

Confirm we are using the correct virtualenv instance of python:

`python --version`

`which python`

`which pip3`

Should all point to the Python v3.x in the virtualenv we created, NOT to the default system python. 

Clone this git repo, using either the HTTP URL (if using a machine whose SSH key is not registered in github) or SSH:
https://github.com/mpetermangis/dfo-spilltracker

`cd ~`

`git clone git@github.com:mpetermangis/dfo-spilltracker.git`
OR 
`git clone https://github.com/mpetermangis/dfo-spilltracker.git`

Install python packages:

`pip3 install -r requirements.txt`

## Database Setup

1. Create a new postgres database user and DB

Check that PostgreSQL was installed correctly by listing the existing databases:

`sudo -u postgres psql -l`

Create a DB user. You will be prompted for a password:

`sudo -u postgres createuser -S -D -R -P spilluser` 

Create a new PostgreSQL database, owned by the database user you just created:

`sudo -u postgres createdb -O spilluser spilldb -E utf-8`

Save the connection string for this DB as an environment variable. This will be picked up by SQLAlchemy in python. 

`sudo nano /etc/environment`

Add this line:

`SPILL_TRACKER_DB_URL=postgresql://spilluser:<password>@localhost/spilldb`

Logout of the server and connect again via ssh. After re-connecting, you should have this enviro var:

`echo SPILL_TRACKER_DB_URL`

## Web Server Setup

We will use uwsgi to serve this Python (flask) web app. Test the configuration by serving locally. First, open a second terminal so that you can see the results:

`cd ~/dfo-spilltracker`

`uwsgi --socket 0.0.0.0:5000 --protocol=http -w wsgi:app`

This means: serve the wsgi app (in file wsgi.py) on local port 5000, using HTTP protocol. Switch to the other terminal and try to access this app: 

`curl localhost:5000` 

If successful, should see a bunch of HTML code for the CCG/DFO Spill Tracker system.  Go back to other terminal and press Ctrl+C to shut down uwsgi for now.  Now try the full command that we will use in supervisor:

`/home/ubuntu/spill/bin/uwsgi --socket 127.0.0.1:3031 --wsgi-file /home/ubuntu/dfo-spilltracker/wsgi.py -H /home/ubuntu/spill --chdir /home/ubuntu/dfo-spilltracker --lazy-apps --processes 4 --threads 2 --stats 127.0.0.1:9191`

That's quite a a mouthful. Let's break it down:

`/home/ubuntu/spill/bin/uwsgi` 

Full path to the uwsgi Python server in our virtual env. 

`--socket 127.0.0.1:3031` 

Internal socket where the app will be accessible. Nginx public-facing web server will proxy requests to this internal socket. 

`--wsgi-file /home/ubuntu/dfo-spilltracker/wsgi.py`

Specify which wsgi file we will use. 

`-H /home/ubuntu/spill`

The path to the Python venv. 

`--chdir /home/ubuntu/dfo-spilltracker` 

Run from this folder. If you don't do this, uwsgi won't be able to find your modules, since it does not know where to look for them, other than the python venv. 

`--lazy-apps`

This option, in contrast to the `--master` option, ensures that each worker is loaded independently. This prevents thread conflicts in the database. Without this, I was getting a very cryptic error message: `sqlalchemy.exc.OperationalError: (OperationalError) SSL error: decryption failed or bad record mac`.  Solution found here: https://stackoverflow.com/a/22753269 

`--processes 4 --threads 2`

uWSGI spawn 4 childs each with 2 threads. 

`--stats 127.0.0.1:9191`

Also spawn a stats server for the web app. 

We will now create a supervisor config to run the uwsgi service. 

### Supervisor setup

The supervisor conf file has already been added to this git repo. Only need to copy it to the supervisor active conf folder, and fill in the postgres password in the environment section:

`sudo cp /home/ubuntu/dfo-spilltracker/conf/supervisor.spill.conf /etc/supervisor/conf.d/supervisor.spill.conf`

`sudo supervisorctl reload`

`sudo supervisorctl restart spill`

Ensure that the server is running:

`sudo tail -f /var/log/supervisor/spill-stderr*.log`

Should see multiple entries like "spawned uWSGI process..." blah blah

### Nginx setup

Disable the default nginx conf in `/etc/nginx/sites-enabled`. Then symlink our conf, keeping the original version (without SSL) as a backup: 

`cd /etc/nginx/sites-enabled`

`sudo ln -s /home/ubuntu/dfo-spilltracker/conf/nginx.spill.conf ./spill.conf`

Now create a file to password-protect the web interface: 

`sudo htpasswd -c /home/ubuntu/spill-users spill`

Choose a password for user "spill"

Confirm that nginx config is ok:

`sudo service nginx restart`

`sudo nginx -t`

### Domain and SSL

For a production service, need to have a domain and SSL enabled.  I got a virtual domain from no-ip.com:  spilltracker.ddns.net.  This point to the IP address of the AWS server. 

To enable SSL. 

`sudo apt-get update`

`sudo apt-get install certbot python-certbot-nginx`

Allow nginx to modify your conf file directly:

`sudo certbot --nginx`

`sudo service nginx restart`

Now the web service should be available through SSL. Backend will continue to be available locally through the port in the uwsgi command.  Try accessing it from an external web browser. 
