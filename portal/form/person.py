from wtforms import Form, TextField, PasswordField, validators

class FindPersonForm(Form):
    name = TextField('Name:')
    
    