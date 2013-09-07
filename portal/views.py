from flask import render_template
from flask import request, redirect, url_for, flash, session

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
                return redirect(url_for('login'))
            else:
                error = changed['message']
    
    return render_template('reset_password.html', env=env, row=row, form=form, error=error)


@app.route("/people/", methods=['GET', 'POST'])
def people():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    rows = []
    if request.method == 'POST':
        person = Person()
        rows = person.find(request.form.get('search',''))
    return render_template('people.html', env=env, rows=rows)


@app.route("/people/<int:person_id>", methods=['GET'])
def person_get(person_id):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))
    
    person = Person()
    p = person.get(person_id)
    
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

    user = User()
    u = user.getall()
    return render_template('admin_list.html', env=env, rows=u)


@app.route("/accounts/<int:person_id>", methods=['GET'])
def accounts(person_id):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

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
    
    p = None 
    form = None
    error = None
    if request.method == "GET":
        if person_id:
            person = Person()
            p = person.get(person_id)
            names = p['name'].split(' ')
            p['username'] = (names[0][0] + names[-1]).lower()
    elif request.method == "POST":
        form = UserAccountForm(request.form)
        if form.validate():
            # Create the user account
            user = User()
            error = user.new({
                'personid': person_id,
                'username': request.form.get('username')
            })
            if error is None:
                return redirect('/accounts/%d' % person_id)
        if not form.validate() or error:
            p = {
                'personid':person_id,
                'username':request.form.get('username',''),
            }
        
    return render_template('admin_new.html', env=env, row=p, form=form, error=error) 


def is_authenticated():
    return 'username' in session

