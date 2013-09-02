from flask import Flask
import os

app = Flask(__name__)

app.debug = True
app.secret_key = os.environ["SECRET_KEY"]

import portal.views
import portal.rest
import portal.sync
