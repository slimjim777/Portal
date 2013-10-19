from flask import Flask
from flask_sslify import SSLify
import os

app = Flask(__name__)
sslify = SSLify(app, permanent=True)

app.debug = False
app.secret_key = os.environ["SECRET_KEY"]

import portal.views
import portal.rest
import portal.sync
