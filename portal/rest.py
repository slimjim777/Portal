from flask import request, redirect, url_for, session, abort, jsonify, flash
from portal import app
from portal.model.crmevent import Event
from portal.model.crmperson import CRMPerson
from portal.model.dbperson import Person
from portal.model.dbuser import User
from portal.views import is_authenticated, is_admin
import time


@app.route("/rest/v1.0/login", methods=['POST'])
def login():
    # Validate the JSON message
    if not request.json:
        abort(400)

    login_action()
    return jsonify({ 'response':'Success' })

def login_action():
    if ('username' not in request.json) or ('password' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"Both 'username' and 'password' must be supplied." })

    user = User()
    u = user.login(request.json['username'], request.json['password'])
    if u:        
        session['username'] = u['username']
        session['access'] = u['access'].split(',')
        session['role'] = u['role']
        session['login_time'] = time.time()
        
        # Set the team-serving groups this person can update
        groups = user.groups(u['personid'])

        session['groups'] = [x['name'] for x in groups]
        session['groups_contact'] = [x['name'] for x in groups if x['contact_only']]
    else:
        abort(403)

@app.route("/rest/v1.0/events", methods=['POST'])
def events():
    """
    Get the Events for Kids Work.
    """
    login_action()
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
    login_action()
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
    login_action()
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


@app.route("/rest/v1.0/person/find", methods=['POST'])
def person_find():
    """
    Called by the portal.
    Find people using name.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    
    person = Person()
    result = person.find(request.json.get('name',''))
    rows = []
    for r in result:
        rows.append({
            'personid': r['personid'],
            'name': r['name'],
            'email': r['email'],
        })
    return jsonify(result=rows)


@app.route("/rest/v1.0/person/groups", methods=['POST'])
def person_groups():
    """
    Called by the portal.
    Find the people in a particular 'team-serving' group.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
        
    groups = request.json.get('groups',[])
    if len(groups)==0:
        return jsonify(result=[])
    
    person = Person()
    rows = person.people_in_groups(groups)
    
    return jsonify(result=rows)
    

@app.route("/rest/v1.0/territory", methods=['POST'])
def territory():
    """
    Called by the portal.    
    Add/remove territory from individual.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('personid' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The Person's 'personid' must be supplied." })    
    if ('action' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'action' must be supplied." })    
    if ('territory' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'territory' must be supplied." })    

    user = User()
    response = user.territory_update(request.json['personid'], request.json['action'], request.json['territory'])
    return jsonify(response)


@app.route("/rest/v1.0/role", methods=['POST'])
def role():
    """
    Called by the portal.    
    Set the role for an individual.
    """
    if not is_authenticated():
        abort(403)

    # Check permissions
    if not is_admin():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('personid' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The Person's 'personid' must be supplied." })    
    if ('role' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'role' must be supplied." })    

    user = User()
    response = user.role_update(request.json['personid'], request.json['role'])
    return jsonify(response)


@app.route("/rest/v1.0/user_group", methods=['POST'])
def user_group():
    """
    Called by the portal.
    Add/remove team-serving group from user.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('personid' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The Person's 'personid' must be supplied." })    
    if ('action' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'action' must be supplied." })    
    if ('group' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'group' must be supplied." })    

    user = User()
    response = user.user_group_update(request.json['personid'], request.json['action'], request.json['group'])
    return jsonify(response)


@app.route("/rest/v1.0/membership", methods=['POST'])
def membership():
    """
    Called by the portal.    
    Add/remove group membership for an individual.
    """
    if not is_authenticated():
        abort(403)

    # Validate the JSON message
    if not request.json:
        abort(400)
    if ('personid' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The Person's 'personid' must be supplied." })    
    if ('action' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'action' must be supplied." })    
    if ('membership' not in request.json):
        return jsonify({ 'response':'Failed', 'error':"The 'membership' must be supplied." })    

    # Update the membership in the database
    person = Person()
    response = person.membership_update(request.json['personid'], request.json['action'], request.json['membership'])

    # Update the membership in CRM
    crm = CRMPerson()
    if request.json['action'] == 'add':
        add_action = True
    else:
        add_action = False    
    crm.crm_login()
    response = crm.person_membership(request.json['personid'], request.json['membership'], add_action)

    return jsonify(response)


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
    login_action()
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
    login_action()
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


@app.route("/rest/v1.0/reset", methods=['POST'])
def reset_request():
    """
    Called by the portal.    
    Initiate the password reset (from the login screen)
    """
    if 'username' in request.json:
        user = User()
        response = user.reset(request.json['username'])
        if response:
            flash("Password reset Email has been sent for username '%s'" % request.json['username'])
        return jsonify({'response':response})
    else:
        return jsonify({'response':False, 'message':'Username must be supplied'})


@app.route("/rest/v1.0/save_password", methods=['POST'])
def save_password():
    """
    Called by the portal.
    Save the new password (from the user account screen)
    """
    if not is_authenticated():
        abort(403)

    if 'personid' in request.json and 'username' in request.json and 'password' in request.json:
        user = User()
        response = user.save_password(request.json['personid'], request.json['username'], request.json['password'])
        if response['response']:
            flash("Password changed successfully")
        return jsonify(response)
    else:
        return jsonify({'response':False, 'message':'Username must be supplied'})

def _register(action):
    login_action()
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




