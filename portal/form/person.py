from wtforms import Form, TextField, PasswordField, IntegerField, validators

class FindPersonForm(Form):
    name = TextField('Name:')
    

class UserAccountForm(Form):
    personid = IntegerField('Person ID', [validators.Required()])
    username = TextField('Username', [validators.Length(min=4, max=40), validators.Required()])
    name = TextField('Name', [validators.Length(max=200)])
    
    