
# Spill Tracker

This readme is the installation guide for the DFO Spill Tracker.

## System Requirements

A Linux server (Ubuntu or Debian) with minimum 4GB memory. 

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

Clone this git repo. 

`cd dfo-spilltracker`

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

Edit the .env file and add `SPILL_TRACKER_DB_URL` as an env var.


## Web Server Setup

We will use uwsgi to serve this Python (flask) web app. Test the configuration by serving locally. First, open a second terminal so that you can see the results:

`cd ~/spilltracker`

`uwsgi --socket 0.0.0.0:5000 --protocol=http -w wsgi:application`

Test serving the wsgi app (in file wsgi.py) on local port 5000, using HTTP protocol. Switch to the other terminal and try to access this app: 

`curl localhost:5000` 

If successful, should see a bunch of HTML code for the CCG/DFO Spill Tracker system.  Go back to other terminal and press Ctrl+C to shut down uwsgi for now.  Now try the full command that we will use in supervisor:

`/home/spill/venv/polrep/bin/uwsgi --socket 127.0.0.1:3031 --wsgi-file /home/spill/spilltracker/wsgi.py -H /home/spill/venv/polrep --chdir /home/spill/spilltracker --lazy-apps --processes 4 --threads 2 --stats 127.0.0.1:9191`

This command consists of:

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

Once this is done, we can send emails using any address that ends with `@marinepollution.ca`.

To test sending emails, use this example code:
https://docs.aws.amazon.com/ses/latest/DeveloperGuide/examples-send-using-smtp.html

The list of SMTP endpoints is here:
https://docs.aws.amazon.com/general/latest/gr/ses.html
Be sure to use the list of SMTP Endpoints, ***NOT*** the list of SES endpoints which is just above it on that page. 


### PostGIS Table for Spill Reports

We cannot do this with a view, because PostGIS requires a full table for setting SRID and adding indexes.  So, we'll have to create a separate spatial table and keep it synchronized with the main one.  In any case, we don't want to turn the main report table into a spatial table, because we only want to have one version (the latest) for each report on the map. 

I created a view that generates the latest version of each spill report, with PostGIS point geometry from lat-lon. This doesn't work in PostGIS as described above.  Then I did  SELECT into another table, where I was able to add a spatial index and set SRID correctly as follows:

`select UpdateGeometrySRID('public', 'report_map_view', 'geometry', 4326);`

`CREATE INDEX idx_report_map_mvw ON public.report_map_mvw USING gist(geometry);`

In the Postgres tables, I created another table to hold a spatial view of the data, with PostGIS geometry. SQLAlchemy, which is used elsewhere in the database, does not play nice with SQLAlchemy.  The postgis table is `report_map_tbl` and there is a simple function that updates each row in this table when the corresponding row in the master table is updated: `update_report_map(report_num)` in postgis_db.py. 


## Geoserver

Geoserver is used to provide WMS access to the spill report data. Geoserver serves one table from postgis, `report_map_tbl`. Note that PostGIS runs independently from Geoserver, and does not require Geoserver.  However, Geoserver requires PostGIS to be running with the table mentioned above. Without this, Geoserver has nothing to serve to WMS clients.  
