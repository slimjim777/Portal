from flask import Flask
from flask_sslify import SSLify
import os

app = Flask(__name__)

if not os.environ.get("PORTAL_DEBUG"):
    sslify = SSLify(app, permanent=True)
    app.debug = False
else:
    app.debug = True

app.secret_key = os.environ["SECRET_KEY"]

import portal.views
import portal.rest
import portal.sync
