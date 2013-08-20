from flask import request, redirect, url_for, session, abort, jsonify
from portal import app
from portal.model.synccrm import SyncCRM
from portal.views import is_authenticated

@app.route("/sync/v1.0/lastsync", methods=['GET'])
def lastsync():
    """
    Get last sync times of each record type
    """
    if not is_authenticated():
        abort(403)

    sync = SyncCRM()
    sync_list = sync.lastsync()
    return jsonify( result=sync_list )

