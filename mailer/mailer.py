import os
import sys
import ConfigParser
import json
from HTMLParser import HTMLParser

import bottle
from bottle import request, response, hook, route, abort
from bottle import post, get, put, delete

from urlparse import urlparse


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

_allow_origin = '*'
_allow_methods = 'PUT, GET, POST, DELETE, OPTIONS'
_allow_headers = 'Authorization, Origin, Accept, Content-Type, X-Requested-With'

@hook('after_request')
def enable_cors():
    '''Add headers to enable CORS'''

    response.headers['Access-Control-Allow-Origin'] = _allow_origin
    response.headers['Access-Control-Allow-Methods'] = _allow_methods
    response.headers['Access-Control-Allow-Headers'] = _allow_headers

@route('/', method = 'OPTIONS')
@route('/<path:path>', method = 'OPTIONS')
def options_handler(path = None):
    return

@route('/contact', method = 'POST')
def contact():
    trusted_domains = config.get('domains', 'trusted').split(',')

    referer = urlparse(request.headers.get('Referer'))

    if referer.netloc not in trusted_domains:
        response.status = 401
        return json.dumps({'error': 'Referrer domain not trusted', "referer": referer})

    response.headers['Content-Type'] = 'application/json'

    if not request.forms.get('name'):
        response.status = 400
        return json.dumps({'error': 'Name is required.'})

    if not request.forms.get('email'):
        response.status = 400
        return json.dumps({'error': 'Email is required.'})

    if not request.forms.get('message'):
        response.status = 400
        return json.dumps({'error': 'Message is required.'})

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
        return json.dumps({"data": "Message sent."})
    else:
        response.status = 500
        return json.dumps({"error": r.text})


@route('/subscribe', method = 'POST')
def subscribe():
    trusted_domains = config.get('domains', 'trusted').split(',')

    referer = urlparse(request.headers.get('Referer'))

    if referer.netloc not in trusted_domains:
        response.status = 401
        return json.dumps({'error': 'Referrer domain not trusted', "referer": referer})

    response.headers['Content-Type'] = 'application/json'

    if not request.forms.get("email_address"):
        response.status = 400
        return json.dumps({'error': 'Email address is required'})

    # We're gonna send a confirmation email first to make sure they are signing up their own email
    with open(config.get('subscriber', 'email_template')) as f:
        template = f.read()

    r = requests.post(
            "https://api.mailgun.net/v3/" + config.get('mailgun', 'domain') + "/messages",
            auth=('api', config.get('mailgun', 'api_key')),
            data={
                "from": request.forms.get('name') + " <" + request.forms.get('email') + ">",
                "to": request.forms.get("email_address"),
                "subject": config.get('subscriber', 'subject'),
                "html": template
            }
    )

    if r.status_code == 200:
        response.status = 200
        return json.dumps({"data": "Message sent."})
    else:
        response.status = 500
        return json.dumps({"error": r.text})


if __name__ == '__main__':
    bottle.run(server='gunicorn', host = '127.0.0.1', port = 8000)

