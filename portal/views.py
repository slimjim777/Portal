from flask import render_template
from flask import request, redirect, url_for, flash, session, abort

from portal.form.login import LoginForm
from portal.form.person import UserAccountForm, UserResetPasswordForm
from portal import app
from portal.model.models import User
from portal.model.models import Person
import os
import gevent


env = {
    'TINFOIL_NAME':os.environ['TINFOIL_NAME'],
    'TINFOIL_CONTENT':os.environ['TINFOIL_CONTENT'],
}

@app.route("/", methods=['GET', 'POST'])
def index():
    # Redirect if already logged-in
    if session.get('username'):
        return redirect(url_for('people'))

    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        # Attempt to login 
        user = User()
        u = user.login(form.username.data, form.password.data)
        if u:        
            flash('Welcome %s!' % u['name'])
            session['username'] = u['username']
            session['access'] = u['access'].split(',')
            session['role'] = u['role']
            
            # Set the team-serving groups this person can update
            groups = user.groups(u['personid'])
            session['groups'] = [x['name'] for x in groups]
            return redirect(url_for('people'))
        else:
            form.username.errors.append('Username or password is incorrect.')
    return render_template('login.html', env=env, form=form)


@app.route("/logout/", methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/reset/<reset_code>/<int:personid>", methods=['GET','POST'])
def reset_password(reset_code, personid):
    # Check that the reset code is valid
    user = User()
    check = user.reset_validate(personid, reset_code)
    row = {
        'reset': reset_code,
        'personid': personid,
        'check': check,
    }
    error = None

    form = UserResetPasswordForm(request.form)
    if request.method == 'POST' and form.validate():
        # Save the changed password
        if form.password1.data==form.password2.data:
            changed = user.save_password(personid, form.username.data, form.password1.data)
            if changed['result']:
                flash('Password changed successfully.')
                return redirect(url_for('index'))
            else:
                error = changed['message']
    
    return render_template('reset_password.html', env=env, row=row, form=form, error=error)


@app.route("/people/", methods=['GET', 'POST'])
def people():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    rows = []
    search=''
    person_stack = []
    next_person = ''
    if request.method == 'POST':
        person = Person()
        
        search = request.form.get('search','')
        person_stack = request.form.get('person_stack','').split('|')
        
        # Set the 'from' name from the direction
        if request.form.get('direction','forward')=='forward':
            rows = person.find(search, request.form.get('next_person',''))
        else:
            person_stack.pop()
            if len(person_stack)>0:
                prev_person = person_stack[-1]
            else:
                prev_person = ''
            rows = person.find(search, prev_person)
        
        # Define the previous and next people names from the results
        if rows:
            if request.form.get('direction','forward')=='forward':
                first = rows[0].get('name','')
                person_stack.append(first)
        
            next_person = rows[-1].get('name','')
            
    return render_template('people.html', env=env, rows=rows, search=search, next_person=next_person, person_stack='|'.join(person_stack))


@app.route("/people/<int:person_id>", methods=['GET'])
def person_get(person_id):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))
    
    person = Person()
    p = person.get(person_id)
    p.update(person.group_membership(person_id))
    
    return render_template('person.html', env=env, row=p)


@app.route("/settings/", methods=['GET'])
def settings():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    user = User()
    u = user.details(username=session['username'])
    return render_template('settings.html', env=env, row=u)


@app.route("/accounts/", methods=['GET'])
def accounts_list():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    # Check permissions
    if not is_admin():
        abort(403)

    user = User()
    u = user.getall()
    return render_template('admin_list.html', env=env, rows=u)


@app.route("/accounts/<int:person_id>", methods=['GET'])
def accounts(person_id):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    # Check permissions
    if not is_admin():
        abort(403)

    user = User()
    u = user.details(personid=person_id)
    g = user.groups(person_id)
    groups = user.groups_unselected(person_id)
    return render_template('admin.html', env=env, row=u, groups=groups, ug=g)


@app.route("/accounts/new/", methods=['GET'])
@app.route("/accounts/new/<int:person_id>", methods=['GET','POST'])
def accounts_new(person_id=None):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    # Check permissions
    if not is_admin():
        abort(403)
    
    p = None 
    form = UserAccountForm(request.form)
    error = None
    if person_id:
        person = Person()
        p = person.get(person_id)

    if request.method == "GET" and p:
        # Default the username based on the person's name
        names = p['name'].split(' ')
        form.username.data = (names[0][0] + names[-1]).lower()

    if request.method == "POST":
        if form.validate():
            # Create the user account
            user = User()
            error = user.new({
                'personid': person_id,
                'username': request.form.get('username')
            })
            if error is None:
                return redirect('/accounts/%d' % person_id)
        
    return render_template('admin_new.html', env=env, row=p, form=form, error=error) 


@app.route("/contact/", methods=['GET'])
def contact():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    # Check permissions
    if not is_member():
        abort(403)

    if session['role'] == 'Admin':
        user = User()
        groups = [x['name'].replace('&&','&') for x in user.groupsall()]
    else:
        groups = session['groups']

    return render_template('contact.html', env=env, groups=groups)


def is_authenticated():
    return 'username' in session

def is_admin():
    return session['role']=='Admin'

def is_member():
    return session['role']=='Admin' or len(session['groups'])>0


