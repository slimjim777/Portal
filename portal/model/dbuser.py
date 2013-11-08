import binascii
import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import hashlib
import smtplib
from flask import render_template
import os
from portal import app
from portal.model.models import Database
import re

__author__ = 'jjesudason'


class User(Database):
    TERRITORIES = ['Active','Kidswork']

    @staticmethod
    def _hashed(pwd):
        return hashlib.sha224(os.environ["SALT"] + pwd).hexdigest()

    def login(self, username, password):
        """
        Verify the user login details.
        """
        self.cursor.execute("""
            SELECT * FROM visitor v
            INNER JOIN person p ON p.personid=v.personid
            WHERE username=%s AND password=%s
        """, (username.lower(), self._hashed(password)))
        row = self.cursor.fetchone()

        if row:
            # Update the last login time and remove password reset requests
            sql = 'update visitor set reset=null, reset_expiry=null, last_login=%s where personid=%s'
            self.cursor.execute(sql, (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),row['personid'],))
            self.sqlconn.commit()

        return row

    def details(self, username=None, personid=None):
        sql = """
            select * from visitor v
            inner join person p on p.personid=v.personid
            where
        """
        if username:
            sql += 'username=%s'
            self.cursor.execute(sql, (username,))
        else:
            sql += 'v.personid=%s'
            self.cursor.execute(sql, (personid,))

        user = self.cursor.fetchone()
        if user:
            user = dict(user)
            user['territories'] = self.territories(user['access'])
        return user

    def getall(self):
        # Get the users
        sql = """
            select * from visitor v
            inner join person p on p.personid=v.personid
            order by p.name
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def groups(self, personid):
        # Get the user groups
        sql = """
            select g.*, ug.contact_only from groups g
            inner join user_group ug on ug.groupsid=g.groupsid
            where ug.personid = %s
            order by g.name
        """
        self.cursor.execute(sql, (personid,))
        return self.cursor.fetchall()

    def groups_unselected(self, personid):
        sql = """
            select * from groups
            where groupsid not in (select groupsid from user_group where personid = %s)
            order by name
        """
        self.cursor.execute(sql, (personid,))
        return self.cursor.fetchall()

    def groups_all(self):
        # Get the user groups
        sql = """
            select * from groups order by name
        """
        self.cursor.execute(sql)
        return self.cursor.fetchall()

    def territories(self, access):
        """
        Convert the list of territories into dictionaries that indicate access.
        """
        perms = []
        territories = access.split(',')
        for t in self.TERRITORIES:
            if t in territories:
                perms.append({'name':t, 'access':True})
            else:
                perms.append({'name':t, 'access':False})
        return perms

    def territory_update(self, personid, action, territory):
        """
        Update the territories for a user.
        """
        self.cursor.execute("select access from visitor where personid=%s", (personid,))
        row = self.cursor.fetchone()
        if not row:
            return {'response':'Failed', 'error':'Cannot find the user'}

        app.logger.debug(row)
        territories = row['access'].split(',')
        if action == 'remove' and territory in territories:
            territories.remove(territory)
        elif action == 'add' and territory not in territories:
            territories.append(territory)
            territories.sort()

        # Save the update territory list
        sql = 'update visitor set access=%s where personid=%s'
        self.cursor.execute(sql, (','.join(territories),personid))
        self.sqlconn.commit()
        return {'response':'Success'}

    def role_update(self, personid, role):
        """
        Update the role for a user.
        """
        # Save the update territory list
        sql = 'update visitor set role=%s where personid=%s'
        self.cursor.execute(sql, (role,personid,))
        self.sqlconn.commit()
        return {'response':'Success'}

    def new(self, rec):
        """
        Create the user account.
        """
        sql = 'insert into visitor values (%s,%s,%s,%s,%s)'

        if rec.get('password'):
            pwd = self._hashed(rec['password'])
        else:
            pwd = None
        try:
            self.cursor.execute(sql, (rec['personid'], rec['username'].lower(), pwd,
                                        rec.get('access','Active'),
                                        rec.get('role','Standard'),))
            self.sqlconn.commit()
        except Exception as e:
            return str(e)

        # Send the welcome mail with the account name

        # Send email to reset the password
        self.reset_password(rec['personid'])

        return None

    def reset(self, username):
        """
        Check that the username is valid, if so, reset the password.
        """
        self.cursor.execute('select * from visitor where username=%s', (username,))
        v = self.cursor.fetchone()
        if not v:
            return False

        return self.reset_password(v['personid'])

    def reset_password(self, personid):
        """
        Generate a reset code and expiry date on the User Account.
        """
        # Get the user's email
        self.cursor.execute('select * from person where personid=%s', (personid,))
        p = self.cursor.fetchone()
        if not p:
            return False

        reset = binascii.b2a_hex(os.urandom(24))
        expiry = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
        sql = 'update visitor set reset=%s, reset_expiry=%s where personid=%s'
        self.cursor.execute(sql, (reset,expiry,personid,))
        self.sqlconn.commit()

        self.reset_send_email(personid, p['email'], reset)
        return True

    def save_password(self, personid, username, password):
        """
        Check that the entered username is correct and update the password.
        """
        if not self.check_password_complexity(password):
            return {'response': False, 'message':'The password must be at least 6 characters and contain lowercase, uppercase letters and numbers'}

        sql = 'select * from visitor where personid=%s and username=%s'
        self.cursor.execute(sql, (personid, username.lower(),))
        row = self.cursor.fetchone()
        if not row:
            return {'response': False, 'message':'The username is invalid'}

        # Entered username is correct, update the password
        sql = 'update visitor set password=%s where personid=%s'
        self.cursor.execute(sql, (self._hashed(password),personid,))
        self.sqlconn.commit()

        return {'response': True}

    def reset_validate(self, personid, reset_code):
        """
        Check that the reset code is valid.
        """
        sql = 'select * from visitor where personid=%s and reset=%s'
        self.cursor.execute(sql, (personid,reset_code,))
        if self.cursor.fetchone():
            return True
        else:
            return False

    def reset_send_email(self, personid, email, reset_code):
        body_text = render_template('email_reset.txt', reset_code=reset_code, personid=personid)
        body_html = render_template('email_reset.html', reset_code=reset_code, personid=personid)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset for Lifechurch Portal'
        msg['From'] = os.environ['EMAIL_FROM']
        msg['To'] = email
        msg.attach(MIMEText(body_text, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))

        self.send_email([email], msg)

    @staticmethod
    def send_email(to_list, mimetext):
        server = smtplib.SMTP(os.environ['SMTP_SERVER'] + ':' + os.environ['SMTP_PORT'])
        if os.environ['SMTP_TLS'] == 'True':
            server.starttls()
        server.login(os.environ['SMTP_USERNAME'], os.environ['SMTP_PASSWORD'])
        server.sendmail(os.environ['EMAIL_FROM'], to_list, mimetext.as_string())
        server.quit()

    def user_group_update(self, personid, action, group):
        """
        Update the group for a user.
        """
        params = {
            'personid': personid,
            'name': group.replace('&','&&'),
        }
        if action == 'remove':
            sql = """
                delete from user_group
                where groupsid in (select groupsid from groups where name=%(name)s)
                  and personid=%(personid)s
            """
        elif action == 'add':
            sql = """
                insert into user_group (personid, groupsid, contact_only)
                    (select %(personid)s,groupsid,false from groups where name=%(name)s)
            """
        elif action == 'update':
            sql = """
                update user_group set contact_only=true 
                    where personid=%(personid)s 
                    and groupsid in 
                          (select groupsid from groups where name=%(name)s)
            """
        else:
            return {'response':'Failed', 'error':'Invalid action'}

        self.cursor.execute(sql, params)
        self.sqlconn.commit()
        return {'response':'Success'}

    @staticmethod
    def check_password_complexity(password):
        prog = re.compile('^.*(?=.{6,})(?=.*[a-z])(?=.*[A-Z])(?=.*[\d\W])(?=.*[0-9]).*$')
        if re.match(prog, password):
            return True
        else:
            return False
