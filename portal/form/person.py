from wtforms import Form, TextField, PasswordField, validators

class FindPersonForm(Form):
    lastname = TextField('Lastname:')
    firstname = TextField('First Name:')
    
    