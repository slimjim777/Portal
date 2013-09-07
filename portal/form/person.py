from wtforms import Form, TextField, PasswordField, IntegerField, validators
from wtforms.validators import EqualTo

class FindPersonForm(Form):
    name = TextField('Name:')
    

class UserAccountForm(Form):
    personid = IntegerField('Person ID', [validators.Required()])
    username = TextField('Username', [validators.Length(min=4, max=40), validators.Required()])
    name = TextField('Name', [validators.Length(max=200)])
    

class UserResetPasswordForm(Form):
    username = TextField('Username', [validators.Length(min=6, max=40), validators.Required()])
    password1 = TextField('Password', [validators.Length(min=6, max=40),
                                        validators.Required()])
    password2 = TextField('Confirm Password', [validators.Length(min=6, max=40),
                                                validators.Required(),
                                                EqualTo('password1', message='Passwords must match')])    


