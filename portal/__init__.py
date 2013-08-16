from flask import Flask

app = Flask(__name__)
#app.config.from_envvar('PORTAL_SETTINGS')

import portal.views
import portal.rest

