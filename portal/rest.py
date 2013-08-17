from flask import request, redirect, url_for, session, abort, jsonify
from portal import app
from portal.model.models import User, Event, Person
from portal.views import is_authenticated

@app.route("/rest/v1.0/login", methods=['POST'])
def login():
    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('username' not in request.json) or ('password' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"Both 'username' and 'password' must be supplied." })

    user = User()
    u = user.login(request.json['username'], request.json['password'])
    if u:        
        session['username'] = u['username']
    else:
        abort(403)
       
    return jsonify({ 'response':'Success' })


@app.route("/rest/v1.0/events", methods=['GET'])
def events():
    """
    Get the Events for Kids Work.
    """
    if not is_authenticated():
        abort(403)

    event = Event()
    event_list = event.get_events()
    return jsonify( result=event_list )
    

@app.route("/rest/v1.0/family", methods=['POST'])
def family():
    """
    Scanning of the Family tag.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('family_number' not in request.json) or ('event_id' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"Both 'family_number' and 'event_id' must be supplied." })
    
    person = Person()
    result = person.family(request.json['family_number'], request.json['event_id'])
    return jsonify(result)
    
    
@app.route("/rest/v1.0/person", methods=['POST'])
def person():
    """
    Scanning of the Person tag.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('tag_number' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The Person's 'tag_number' must be supplied." })
    
    person = Person()
    result = person.person(request.json['tag_number'], request.json.get('details'))
    return jsonify(result)


@app.route("/rest/v1.0/sign-in", methods=['POST'])
def sign_in():
    """
    Sign-in a set of people.
    """
    return _register('sign-in')


@app.route("/rest/v1.0/sign-out", methods=['POST'])
def sign_out():
    """
    Sign-out a set of people.
    """
    return _register('sign-out')


@app.route("/rest/v1.0/registrations", methods=['POST'])
def registrations():
    """
    Get the list of people registered for the event.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('event_id' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'event_id' must be supplied." })

    person = Person()
    result = person.registrations(request.json['event_id'])
    return jsonify(result=result)


@app.route("/rest/v1.0/scan", methods=['POST'])
def scan():
    """
    Get the details of the person/family for the tag.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('tag' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'tag' must be supplied." })

    person = Person()
    result = person.scan(request.json['tag'])
    return jsonify(result=result)


def _register(action):
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('family_number' not in request.json) or ('people' not in request.json) or ('event_id' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"Both 'family_number', 'event_id' and 'people' list must be supplied." })
    
    person = Person()
    if action == 'sign-in':
        result = person.sign_in(request.json['family_number'], request.json['people'], request.json['event_id'])
    elif action == 'sign-out':
        result = person.sign_out(request.json['family_number'], request.json['people'], request.json['event_id'])
    else:
        result = {'error': 'Action is not available: %s' % action}
    return jsonify(result)


