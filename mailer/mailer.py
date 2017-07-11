import os
import sys
import ConfigParser
import json

import bottle
from bottle import request, response
from bottle import post, get, put, delete

import requests

# Change me for different config file
config_file_location = "~/mailer_config.ini"

config = ConfigParser.ConfigParser()

try:
    config.read(os.path.expanduser(config_file_location))
except Exception as e:
    sys.exit("Couldn't read config file : " + str(e))

if not config.has_section('mailgun'):
    sys.exit("Mailgun section of config not found!")

required_mailgun_options = ['domain', 'api_key']

for option in required_mailgun_options:
    if option not in config.options('mailgun'):
        sys.exit("Mailgun option " + option + " not found!")

if 'email' not in config.options('receiver'):
    sys.exit("Email in receiver option not set!")

app = bottle.default_app()

@post('/')
def mailer():
    response.headers['Content-Type'] = 'application/json'

    if not request.forms.get('name'):
        return json.dumps("{'error': 'Name is required.'}")

    if not request.forms.get('email'):
        return json.dumps("{'error': 'Email is required.'}")

    if not request.forms.get('message'):
        return json.dumps("{'error': 'Message is required.'}")

    

    r = requests.post(
            "https://api.mailgun.net/v3/" + config.get('mailgun', 'domain') + "/messages",
            auth=('api', config.get('mailgun', 'api_key')),
            data={
                "from": request.forms.get('name') + " <" + request.forms.get('email') + ">",
                "to": config.get('receiver', 'email'),
                "subject": config.get('receiver', 'subject'),
                "text": request.forms.get('message')
            }
    )
   
    if r.status_code == 200:
        response.status = 200
        return json.dumps({"data": r.text})
    else:
        response.status = 500
        return json.dumps({"error": r.text})


if __name__ == '__main__':
    bottle.run(server='gunicorn', host = '127.0.0.1', port = 8000)

