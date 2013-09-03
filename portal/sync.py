from flask import request, redirect, url_for, session, abort, jsonify
from portal import app
from portal.model.synccrm import SyncCRM
from portal.views import is_authenticated

@app.route("/sync/v1.0/startsync", methods=['GET'])
def start_sync():
    #if not is_authenticated():
    #    abort(403)

    sync = SyncCRM()
    sync_rec = sync.start_sync()
    return jsonify( sync_rec )
    

