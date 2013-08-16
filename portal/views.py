from flask import render_template
from flask import request, redirect, url_for, flash, session

from portal.form.login import LoginForm
from portal.form.person import FindPersonForm
from portal import app
from portal.model.models import User


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
            return redirect(url_for('people'))
        else:
            form.username.errors.append('Username or password is incorrect.')
    return render_template('login.html', form=form)
    

@app.route("/people/", methods=['GET', 'POST'])
def people():
    if not is_authenticated():
        flash('Please login to access the Portal')
        return redirect(url_for('index'))

    form = FindPersonForm(request.form)
    if request.method == 'POST' and form.validate():
        return redirect(url_for('people'))
    return render_template('people.html', form=form)



def is_authenticated():
    return 'username' in session

