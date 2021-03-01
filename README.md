
# Spill Tracker

This readme is the installation guide for the DFO Spill Tracker.

## System Requirements

A Linux server (Ubuntu or Debian) with 1GB memory. 

## Geoserver

### Proxy Base URL

Unclear how this is supposed to be set. We have tried the following:

http://marinepollution.ca:8080/geoserver

https://marinepollution.ca/geoserver < with nginx proxy

http://localhost:8080/geoserver

With or without geoserver? 
Maybe without? see: https://gis.stackexchange.com/a/304623

http://localhost:8080

No, that doesn't work, because then it tries to access URLs (from the end-user's browser) like this:
http://localhost:8080/polrep/wms?service=WMS&...
Clearly not going to work, since this request is coming from a remote machine, not localhost. 

And it has to have /geoserver at the end, or we get a URL like:
http://marinepollution.ca:8080/polrep/wms?...

When it's supposed to be:
http://marinepollution.ca:8080/geoserver/polrep/wms?...

Get Capabilities URL:
http://marinepollution.ca:8080/geoserver/ows?service=wms&version=1.3.0&request=GetCapabilities


### PostGIS Table for Spill Reports

We cannot do this with a view, because PostGIS requires a full table for setting SRID and adding indexes.  So, we'll have to create a separate spatial table and keep it synchronized with the main one.  In any case, we don't want to turn the main report table into a spatial table, because we only want to have one version (the latest) for each report on the map. 

I created a view that generates the latest version of each spill report, with PostGIS point geometry from lat-lon. This doesn't work in PostGIS as described above.  Then I did  SELECT into another table, where I was able to add a spatial index and set SRID correctly as follows:

`select UpdateGeometrySRID('public', 'report_map_view', 'geometry', 4326);`

`CREATE INDEX idx_report_map_mvw ON public.report_map_mvw USING gist(geometry);`

However, this still does not work in Geoserver.  Why? Because we also need a primary key: 
`﻿java.io.IOException: Cannot do natural order without a primary key, please add it or specify a manual sort over existing attributes` 

Maybe also have to reproject as Web Mercator?

Restricting access to /geoserver via an auth endpoint works in Nginx, but in Geoserver it causes CORS errors.  Even though CORS is enabled in the Geoserver Jetty config, does not work if we access the web interface via:

https://marinepollution.ca/geoserver

Have to go through:
http://marinepollution.ca:8080/geoserver

Also I tried using ssh tunneling, this did not work either. So we have to leave port 8080 wide open in Amz firewall, not ideal.  There are constant attempts to hack into geoserver. 



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

`virtualenv -p python3 polrep`

`source ~/venv/polrep/bin/activate`

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

Save the connection string for this DB as an environment variable. This will be picked up by SQLAlchemy in python. Create a .env file in the project root folder. 

`cd ~/spilltracker`

`touch .env`

Edit the .env file and add the following env vars:

`SPILL_TRACKER_DB_URL=postgresql://spilluser:<password>@localhost/spilldb`

Open a python console and create salt and secret for the DB logins. In python create a different random string for each of the env vars below:

secrets.token_urlsafe(16)

Add these to .env:

`SPILLDB_SECRET=*******`
`SPILLDB_SALT=*******`

Or, use the following file to make the environment vars global.  But a `.env` file is the better option. 
`sudo nano /etc/environment`

Logout of the server and connect again via ssh. After re-connecting, you should have this enviro var:

`echo SPILL_TRACKER_DB_URL`

## Full-text search

This might work:
https://github.com/blakev/Flask-WhooshAlchemy3
https://github.com/blakev/Flask-WhooshAlchemy3/commit/9a3c9d00f69a6d69903d9750596976304fab5fab

## Flask Initialization

Good example code:
https://gist.github.com/skyuplam/ffb1b5f12d7ad787f6e4

Flask-security templates are here:
https://github.com/mattupstate/flask-security

## Troubleshooting

**None** of the Flask-security endpoints are working, such as /login, /reset. 
Why? Because my browser had a previously-stored session which was being used, so I was already logged in. Need to logout first, hit this endpoint:
http://0.0.0.0:5000/logout
Now it's working as expected. 

## Testing with SSL on localhost

Some functions of the server, especially related to login/registration page, require SSL. This is a pain when testing on localhost. In Chrome, go to:
chrome://flags/#allow-insecure-localhost
Then set "Allow invalid certificates for resources loaded from localhost" to Enabled. 
In Flask, run the app with `ssl_context='adhoc'`
Yes, this works, no more warnings! 

### Creating a self-signed cert

This should not be needed if running flask with SSL adhoc, but just in case:
https://blog.miguelgrinberg.com/post/running-your-flask-application-over-https


## Web Server Setup

We will use uwsgi to serve this Python (flask) web app. Test the configuration by serving locally. First, open a second terminal so that you can see the results:

`cd ~/spilltracker`

`uwsgi --socket 0.0.0.0:5000 --protocol=http -w wsgi:application`

Test serving the wsgi app (in file wsgi.py) on local port 5000, using HTTP protocol. Switch to the other terminal and try to access this app: 

`curl localhost:5000` 

If successful, should see a bunch of HTML code for the CCG/DFO Spill Tracker system.  Go back to other terminal and press Ctrl+C to shut down uwsgi for now.  Now try the full command that we will use in supervisor:

`/home/spill/venv/polrep/bin/uwsgi --socket 127.0.0.1:3031 --wsgi-file /home/spill/spilltracker/wsgi.py -H /home/spill/venv/polrep --chdir /home/spill/spilltracker --lazy-apps --processes 4 --threads 2 --stats 127.0.0.1:9191`

That's quite a a mouthful. Let's break it down:

`/home/spill/venv/polrep/bin/uwsgi` 

Full path to the uwsgi Python server in our virtual env. 

`--socket 127.0.0.1:3031` 

Internal socket where the app will be accessible. Nginx public-facing web server will proxy requests to this internal socket. 

`--wsgi-file /home/spill/spilltracker/wsgi.py`

Specify which wsgi file we will use. 

`-H /home/spill/venv/polrep`

The path to the Python venv. 

`--chdir /home/spill/spilltracker` 

Run from this folder. If you don't do this, uwsgi won't be able to find your modules, since it does not know where to look for them, other than the python venv. 

`--lazy-apps`

This option, in contrast to the `--master` option, ensures that each worker is loaded independently. This prevents thread conflicts in the database. Without this, I was getting a very cryptic error message: `sqlalchemy.exc.OperationalError: (OperationalError) SSL error: decryption failed or bad record mac`.  Solution found here: https://stackoverflow.com/a/22753269 

`--processes 4 --threads 2`

uWSGI spawn 4 children each with 2 threads. 

`--stats 127.0.0.1:9191`

Also spawn a stats server for the web app. 

We will now create a supervisor config to run the uwsgi service. 

### Supervisor setup

The supervisor conf file has already been added to this git repo. Only need to copy it to the supervisor active conf folder, and fill in the postgres password in the environment section:

`sudo cp /home/spill/spilltracker/conf/supervisor.spill.conf /etc/supervisor/conf.d/supervisor.spill.conf`

`sudo supervisorctl reload`

`sudo supervisorctl restart spill`

Ensure that the server is running:

`sudo tail -f /var/log/supervisor/spill-stderr*.log`

Should see multiple entries like "spawned uWSGI worker..." blah blah

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

### Domain Registration

For a production service, need to have a domain and SSL enabled.  We registered the domain `marinepollution.ca` using Amazon Route 53, and added an A record pointing to the Elastic IP address of the AWS server.  This IP address is shown on the Instances page: https://ca-central-1.console.aws.amazon.com/ec2/v2/home?region=ca-central-1#Instances:instanceState=running
The current IP address is shown in the Elastic IP column: 52.60.122.16

### Enabling SSL

All modern websites must use Secure Socket Layer (SSL) with a valid SSL certificate. To create an SSL cert, follow these steps: 

`sudo apt-get update`

`sudo apt-get install certbot python-certbot-nginx`

Allow nginx to modify your conf file directly:

`sudo certbot --nginx`

`sudo service nginx restart`

Now the web service should be available through SSL. Backend will continue to be available locally through the port in the uwsgi command.  Try accessing it from an external web browser. 

## Email Setup

Before doing this, we need to have a registered domain.  For this project, we registered the domain `marinepollution.ca` and added an A record for the Elastic IP address assigned to the server. 

We are using Amazon's Simple Email Service (SES) to send emails using Simple Mail Transfer Protocol (SMTP).  First, we need to add this domain so that we can send email from any address `@marinepollution.ca`.  In the SES main screen, click Manage Identities.  If the domain is not already listed under Domain Identities, click Verify a New Domain. You will be prompted to add a few DNS records for this domain, to allow sending emails.  Since we registered the domain using Amazon Route 53, these DNS records can be created automatically, simply click the Use Route 53 button at bottom-right.  Wait a minute and refresh the page, the domain should have green status for all three of these: Verification Status, DKIM Status, Enabled for Sending. 

We also need to create and download SMTP credentials.  The credentials are only shown once; be sure to save the credentials file in a safe place. 

Once this is done, we can send emails using any address that ends with `@marinepollution.ca`, for example:
`updates@marinepollution.ca`
`notifications@marinepollution.ca`
`no-reply@marinepollution.ca`

To test sending emails, use this example code:
https://docs.aws.amazon.com/ses/latest/DeveloperGuide/examples-send-using-smtp.html

The list of SMTP endpoints is here:
https://docs.aws.amazon.com/general/latest/gr/ses.html
Be sure to use the list of SMTP Endpoints, ***NOT*** the list of SES endpoints which is just above it on that page. 

Any newly verified domain is put in the Amazon SES Sandbox by default, with the following restrictions:
https://docs.aws.amazon.com/ses/latest/DeveloperGuide/request-production-access.html
This page also describes how to get out of the sandbox.  It is a good idea to send a number of test emails while still in the sandbox, and ensure that the receiving domain does not mark them as Spam or suspicious.  After ensuring that emails are consistently being delivered, then follow the instructions to get out of the sandbox. 


