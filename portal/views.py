from flask import render_template
from flask import request, redirect, url_for, flash, session

from portal.form.login import LoginForm
from portal.form.person import FindPersonForm
from portal import app
from portal.model.models import User
from portal.model.models import Person


@app.route("/", methods=['GET', 'POST'])
def index():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        # Attempt to login to the sqlite database   
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
    return render_template('login.html', form=form)


@app.route("/logout/", methods=['GET'])
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route("/people/", methods=['GET', 'POST'])
def people():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    rows = []
    if request.method == 'POST':
        person = Person()
        rows = person.find(request.form.get('search',''))
    return render_template('people.html', rows=rows)


@app.route("/people/<int:person_id>", methods=['GET'])
def person_get(person_id):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))
    
    person = Person()
    p = person.get(person_id)
    
    return render_template('person.html', row=p)


@app.route("/settings/", methods=['GET'])
def settings():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    user = User()
    u = user.details(username=session['username'])
    return render_template('settings.html', row=u)


@app.route("/accounts/", methods=['GET'])
def accounts_list():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    user = User()
    u = user.getall()
    return render_template('admin_list.html', rows=u)


@app.route("/accounts/<int:person_id>", methods=['GET'])
def accounts(person_id):
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    user = User()
    u = user.details(personid=person_id)
    g = user.groups(person_id)
    groups = user.groups_unselected(person_id)
    return render_template('admin.html', row=u, groups=groups, ug=g)


@app.route("/accounts/new/", methods=['GET'])
def accounts_new():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    return render_template('admin_new.html') 


def is_authenticated():
    return 'username' in session

