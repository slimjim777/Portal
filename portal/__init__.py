from flask import Flask
from flask_sslify import SSLify
import os
import logging

# Default the encoding to Unicode
import sys
reload(sys)
sys.setdefaultencoding('UTF8')

app = Flask(__name__)

if not os.environ.get("PORTAL_DEBUG"):
    sslify = SSLify(app, permanent=True)
    app.debug = False

    # Logging level
    stream_handler = logging.StreamHandler()
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
else:
    app.debug = True

app.secret_key = os.environ["SECRET_KEY"]

app.logger.info('Portal Start-Up')

import portal.views
import portal.rest
import portal.sync
