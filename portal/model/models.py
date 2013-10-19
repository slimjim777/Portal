# -*- coding: utf-8 -*-
from portal.model.sagecrm import Connection
from flask import session
from flask import render_template
from portal import app
import re
import psycopg2
import psycopg2.extras
import os, datetime, binascii
import urlparse
import hashlib, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class Database(object):

    def __init__(self):
        urlparse.uses_netloc.append("postgres")
        url = urlparse.urlparse(os.environ["DATABASE_URL"])
        
        self.sqlconn = psycopg2.connect(
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )


class User(object):
    TERRITORIES = ['Active','Kidswork']

    def __init__(self):
        db = Database()
        self.sqlconn = db.sqlconn
        self.cursor = self.sqlconn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
    def _hashed(self, pwd):
        return hashlib.sha224(os.environ["SALT"] + pwd).hexdigest()

    def login(self, username, password):
        """
        Verify the user login details.
        """
        self.cursor.execute("""
            SELECT * FROM visitor v 
            INNER JOIN person p ON p.personid=v.personid 
            WHERE username=%s AND password=%s
        """, 
        (username.lower(), self._hashed(password)))
        row = self.cursor.fetchone()
        
        if row:
            # Update the last login time and remove password reset requests
            sql = 'update visitor set reset=null, reset_expiry=null, last_login=%s where personid=%s'
            self.cursor.execute(sql, (datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),row['personid'],))
            self.sqlconn.commit()
        
        return row;
            
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
            select g.* from groups g
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

    def groupsall(self):
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
        if action=='remove' and territory in territories:
            territories.remove(territory)
        elif action=='add' and territory not in territories:
            territories.append(territory)
            territories.sort()
            
        # Save the update territory list
        sql = 'update visitor set access=%s where personid=%s'
        self.cursor.execute(sql, (','.join(territories),personid))
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
    
    def send_email(self, to_list, mimetext):
        server = smtplib.SMTP(os.environ['SMTP_SERVER'] + ':' + os.environ['SMTP_PORT'])
        if os.environ['SMTP_TLS']=='True':
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
                insert into user_group (personid, groupsid)
                    (select %(personid)s,groupsid from groups where name=%(name)s)
            """
        else:
            return {'response':'Failed', 'error':'Invalid action'}
        
        self.cursor.execute(sql, params)
        self.sqlconn.commit()
        return {'response':'Success'}
        
    def check_password_complexity(self, password):
		prog = re.compile('^.*(?=.{6,})(?=.*[a-z])(?=.*[A-Z])(?=.*[\d\W])(?=.*[0-9]).*$')
		if re.match(prog, password):
		    return True
		else:
		    return False
        
        
class SageCRMWrapper(object):
    def __init__(self):
        self.connection = None
        db = Database()
        self.sqlconn = db.sqlconn
        self.cursor = self.sqlconn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
           
    def crm_login(self):
        self.connection = Connection(os.environ['SAGE_WSDL'])
        self.connection.login( os.environ['SAGE_USER'], os.environ['SAGE_PASSWORD'] )
        

class Event(SageCRMWrapper):
     def get_events_crm(self):
        """
        Get the Kids Work events from Sage CRM.
        """
        events = self.connection.client.service.query("lcev_type='KidsWork' and lcev_status='Active'", "lifeEvent")
        
        event_list = []
        for e in events.records:
            event_list.append({
                'event_id': e.eventid,
                'name': e.name,
                })
        
        return event_list
        
     def get_events(self):
        """
        Get the Kids Work events from the local database.
        """
        self.cursor.execute("SELECT * FROM event WHERE type='Kidswork'")
        
        event_list = []
        for e in self.cursor:
            event_list.append({
                'event_id': e['eventid'],
                'name': e['name'],
                })
        
        return event_list    
        

class Person(SageCRMWrapper):

    def family_upsert(self, record):
        """
        Update or insert the provided family record.
        """
        if 'familyid' not in record:
            return False
            
        # Try updating the record and get the rowcount to see if it worked
        sql_update = """
            UPDATE family 
            SET name=%(name)s, tagnumber=%(tagnumber)s, territory=%(territory)s
            WHERE familyid=%(familyid)s"""
        self.cursor.execute(sql_update, record)
        if self.cursor.rowcount > 0:
            # Updated an existing record
            self.sqlconn.commit()
        else:
            # Create a new family record
            sql_insert = """
                INSERT INTO family 
                VALUES (%(familyid)s,%(name)s,%(tagnumber)s,%(territory)s
                )"""
            self.cursor.execute(sql_insert, record)
            self.sqlconn.commit()
            
        return True
 
 
    def person_upsert(self, record):
        """
        Update or insert the provided person record.
        """
        if 'personid' not in record:
            return False
        
        #app.logger.debug(record)
        # Try updating the record and get the rowcount to see if it worked
        sql_update = """
            UPDATE person 
            SET name=%(name)s, family_tag=%(family_tag)s, tagnumber=%(tagnumber)s,
            type=%(type)s, kids_group=%(kids_group)s, kids_team=%(kids_team)s,
            school_year=%(school_year)s, dob=%(dob)s, medical_info=%(medical_info)s,
            medical_notes=%(medical_notes)s,territory=%(territory)s,
            firstname=%(firstname)s, gender=%(gender)s,
            marital_status=%(marital_status)s, lifegroup=%(lifegroup)s, address1=%(address1)s,
            address2=%(address2)s, city=%(city)s, postcode=%(postcode)s, country=%(country)s,
            home_phone=%(home_phone)s, mobile_phone=%(mobile_phone)s, email=%(email)s,
            baptised=%(baptised)s, salvation=%(salvation)s 
            WHERE personid=%(personid)s
        """
        self.cursor.execute(sql_update, record)
        if self.cursor.rowcount > 0:
            # Updated an existing record
            self.sqlconn.commit()
        else:
            # Create a new person record (field order must match the table)
            sql_insert = """
                INSERT INTO person 
                VALUES (%(personid)s,%(name)s,%(family_tag)s,%(tagnumber)s,%(type)s,
                %(kids_group)s,%(kids_team)s,%(school_year)s,%(dob)s,
                %(medical_info)s,%(medical_notes)s,%(territory)s,%(firstname)s,%(gender)s,
                %(marital_status)s,%(lifegroup)s,%(address1)s,%(address2)s,%(city)s,
                %(postcode)s,%(country)s,%(home_phone)s,%(mobile_phone)s,%(email)s, 
                %(baptised)s,%(salvation)s
                )"""
            self.cursor.execute(sql_insert, record)
            self.sqlconn.commit()
            
        # Update the group memberships
        if 'team_serving' in record:
            self.group_membership_update(record['personid'], record['team_serving'])
            
        return True    

 
    def group_membership_update(self, personid, group_names):
        """
        Update the group membership for the person by deleting the existing ones
        and adding the current memberships.
        """
        # Delete existing memberships
        sql_delete = 'delete from membership where personid=%s'
        self.cursor.execute(sql_delete, (personid,))
        
        # Add the current memberships
        if len(group_names)>0:
            names = tuple(x.replace('&','&&') for x in group_names)
            sql_insert = """
                insert into membership (personid,groupsid)
                    select %s, groupsid from groups where name in %s
            """
            self.cursor.execute(sql_insert, (personid,names,))     
            self.sqlconn.commit()


    def people_in_groups(self, groups):
        names = tuple(x.replace('&','&&') for x in groups)
        territories = tuple(x for x in session['access'])
        sql = """
            select personid, name, email, home_phone, mobile_phone from person 
            where personid in 
                (select personid from membership m 
                    inner join groups g on m.groupsid=g.groupsid 
                    where g.name in %s)
            and territory in %s
        """
        people = []
        self.cursor.execute(sql, (names,territories,))
        rows = self.cursor.fetchall()

        if not rows:
            return []
       
        for r in rows:
            people.append( dict(r) )
                   
        return people


    def membership_update(self, personid, action, membership):
        """
        Update the membership for a person.
        """
        params = {
            'personid': personid,
            'name': membership.replace('&','&&'),
        }
        if action == 'remove':
            sql = """
                delete from membership 
                where groupsid in (select groupsid from groups where name=%(name)s) 
                  and personid=%(personid)s 
            """
        elif action == 'add':
            sql = """
                insert into membership (personid, groupsid)
                    (select %(personid)s,groupsid from groups where name=%(name)s)
            """
        else:
            return {'response':'Failed', 'error':'Invalid action'}
        
        self.cursor.execute(sql, params)
        self.sqlconn.commit()
        return {'response':'Success'}
  
 
    def groups_upsert(self, record):
        """
        Update or insert the team serving record.
        """
        if 'groupsid' not in record:
            return False
            
        #app.logger.debug(record)
        # Try updating the record and get the rowcount to see if it worked
        sql_update = """
            UPDATE groups
            SET code=%(code)s, name=%(name)s 
            WHERE groupsid=%(groupsid)s 
        """
        self.cursor.execute(sql_update, record)
        if self.cursor.rowcount > 0:
            # Updated an existing record
            self.sqlconn.commit()
        else:
            # Create a new person record (field order must match the table)
            sql_insert = """
                INSERT INTO groups 
                VALUES (%(groupsid)s,%(name)s,%(code)s)
                """
            self.cursor.execute(sql_insert, record)
            self.sqlconn.commit()
            
        return True                       

    def groups_sync_deletion(self, group_ids):
        """
        Use the list of current group Ids to remove extra ones in the portal database.
        This needs to be done to sync deletions.
        """
        groups = tuple(x for x in group_ids)
        sql = "delete from groups where groupsid not in %s"
        self.cursor.execute(sql, (groups,))
        self.sqlconn.commit()        
        
            
    def family(self, family_number, event_id):
        """
        Get the check to see if any children are signed-in for this tag using the local database.
        """
        # Get the family record for details
        family_record = self._family(family_number)

        # Check for event registrations for this date
        registered = self._reg_list(family_number, event_id)
        family_record.update(registered)
        
        return family_record


    def _reg_list(self, family_number, event_id):
        today = datetime.date.today().isoformat()        
        sql = """select p.*, r.status from registration r 
              inner join person p on person_tag=tagnumber 
              where r.family_tag=%s and r.eventid=%s and r.event_date=%s"""
        self.cursor.execute(sql, (family_number, event_id, today,))

        signed_in = []
        signed_out = []
        for p in self.cursor:
            print p
            person = {
                'name': p['name'],
                'personid': p['personid'],
                'tagnumber': p['tagnumber'],
                'parentid': p['family_tag'],
            }
            if p['status']=='Signed-In':
                signed_in.append( person )
            elif p['status']=='Signed-Out':
                signed_in.append( person )
                
        return {'signed_in':signed_in, 'signed_out':signed_out}     


    def family_crm(self, family_number, event_id):
        """
        Get the check to see if any children are signed-in for this tag.
        """
        # Get the family record for details
        family_record = self._family(family_number)

        # Check for event registrations for this date
        today = datetime.date.today().isoformat()
        where = "oppo_customerref='%s' and oppo_c_eventid=%s and oppo_opened>='%s 00:00:00' and oppo_opened<='%s 23:59:59'" % (family_number, event_id, today, today)

        reg_list = self.connection.client.service.query(where, "Opportunity")
        registered = self._registrations(reg_list)
        family_record.update(registered)
        return family_record
    
    
    def person(self, tag_number, details=None):
        """
        Get the person's details from the tag number.
        This can fetch full details for a person as well.
        """
        return self._person(tag_number=tag_number, details=details)
        

    def sign_in(self, family_number, people, event_id):
        """
        Sign-in a set of kids using a family tag and a list of Person tag numbers.
        """
        return self._register(family_number, people, event_id, 'Signed-In', 'In Progress')


    def sign_out(self, family_number, people, event_id):
        """
        Sign-out a set of kids using a family tag and a list of Person tag numbers.
        """
        return self._register(family_number, people, event_id, 'Signed-Out', 'Won')


    def registrations(self, event_id):
        """
        Get the registrations for the event from local database.
        """
        today = datetime.date.today().isoformat()
        
        self.cursor.execute("select * from registration where eventid=%s and event_date=%s", (event_id, today,))
        rows = self.cursor.fetchall()
        
        if not rows:
            return []
        
        records = []
        for o in rows:
            record = {
                'stage': o['status'],
            }
            
            # Lookup the Person
            p = self._person(tag_number=o['person_tag'], details=True)
            record.update(p)
            
            records.append(record)
        
        return records


    def registrations_crm(self, event_id):
        """
        Get the registrations for the event.
        """
        today = datetime.date.today().isoformat()
        where = "oppo_c_eventid=%s and oppo_opened>='%s 00:00:00' and oppo_opened<='%s 23:59:59'" % (event_id, today, today)
        reg_list = self.connection.client.service.query(where, "Opportunity")
        
        if 'records' not in reg_list:
            return []
        
        records = []
        for o in reg_list.records:
            record = {
                'stage': o.stage,
            }
            
            # Lookup the Person
            p = self._person(person_id=o.primarypersonid, details=True)
            record.update(p)
            
            records.append(record)
        
        return records


    def scan(self, tag):
        """
        Get the details of the person/family from the tag.
        """
        prefix = tag[0:1]
        tag_number = tag[1:]
        
        if prefix == 'F': 
            record = self._family(tag_number)
        elif prefix == 'C' or prefix == 'L':
            record = self._person(tag_number=tag_number, details=True)
        else:
            record = {'error': 'The format of the tag appears to be invalid.'}
            
        return record


    def find(self, search, from_person='', limit=30):
        """
        Search for people by name.
        """
        ids = tuple(x for x in session['access'])
        sql = """select * from person where name ilike '%%'||%s||'%%' and territory in %s 
        and name >= %s 
        order by name 
        limit %s
        """
        self.cursor.execute(sql, (search,ids,from_person,limit,))
        
        rows = self.cursor.fetchall()
        if not rows:
            return []
            
        return rows


    def get(self, personid):
        """
        Get a person by their ID.
        """
        self.cursor.execute("select * from person where personid=%s", (personid,))
        row = self.cursor.fetchone()
        if row:
            p = dict(row)
            return p
        else:
            return row


    def group_membership(self, personid):
        """
        Get the group membership and groups that the person is not a part of.
        """
        # Get the groups the person is in
        sql = """
            select g.name from membership m 
            inner join groups g on m.groupsid=g.groupsid 
            where personid=%s 
            order by g.name
        """
        self.cursor.execute(sql, (personid,))
        groups = []
        for g in self.cursor.fetchall():
            g['name'] = g['name'].replace('&&','&')
            groups.append(dict(g))

        # Get the groups the person is not in
        sql = """
            select g.name from groups g 
            where g.groupsid not in 
             (select m.groupsid from membership m where m.groupsid=g.groupsid 
              and m.personid=%s )
            order by g.name
        """
        self.cursor.execute(sql, (personid,))
        groups_not = []
        for g in self.cursor.fetchall():
            g['name'] = g['name'].replace('&&','&')
            groups_not.append(dict(g))

        return {
            'team_serving': groups,
            'team_serving_not': groups_not,
            }
            

    def _register(self, family_number, people, event_id, stage, status):
        print family_number, people, event_id, stage, status
    
        today = datetime.date.today().isoformat()
        for p in people:
            # Check if the registration (Opportunity) record exists
            sql = "select * from registration where person_tag=%s and family_tag=%s and eventid=%s and event_date=%s"
            self.cursor.execute(sql, (p, family_number, event_id, today,))
            row = self.cursor.fetchone()
            print "---row", row
            
            if row:
                # Update the existing record
                self.cursor.execute("update registration set status=%s where registrationid=%s", (stage, row['registrationid'],))
                self.sqlconn.commit()              
            else:
                # Add a new registration for the person
                sql = "insert into registration (person_tag, family_tag, eventid, event_date, status) values (%s,%s,%s,%s,%s)"
                self.cursor.execute(sql, (p, family_number, event_id, today, stage,))
                self.sqlconn.commit()
                
        return {"result":"success"}


    def _family(self, family_number):
        """
        Get family details from the local database.
        """
        self.cursor.execute("SELECT * FROM family WHERE tagnumber=%s", (family_number,))
        row = self.cursor.fetchone()
        
        if row:
            # Get the children for the parent
            self.cursor.execute("SELECT * FROM person WHERE family_tag=%s", (family_number,))
            children = []
            
            for c in self.cursor:
                child = {
                    'name': c['name'],
                    'personid': c['personid'],
                    'tagnumber': c['tagnumber'],
                    'group': c['kids_group'],
                }
                children.append(child)                
        
            # Format the family record
            record = {
                'tagnumber': row['tagnumber'],
                'parent_name': row['name'],
                'children': children,
            }
        else:
            record = {'error': 'Cannot find Family record for the parent tag ' + family_number}           
        return  record
        
        
    def _family_crm(self, family_number):
        family_list = self.connection.client.service.query("comp_c_familynumber=" + family_number, "Company")
        if 'records' not in family_list:
            return {'error': 'Cannot find Family record for the parent tag ' + family_number}
        
        # Store the family details
        f = family_list.records[0]
        parent_name = f.name
        if 'c_salutation' in f:
            parent_name = f.c_salutation + ' ' + parent_name

        # Get the children's names in the family
        children = []
        if 'records' in f.people:
            for p in f.people.records:
                child = {
                    'name': p.firstname + ' ' + p.lastname,
                    'personid': p.personid,
                    'tagnumber': p.c_tag_number,
                    'group': getattr(p, 'c_kids_group', ''),
                }
                children.append(child)
                
        return {
            'tagnumber': family_number,
            'parent_name': parent_name,
            'children': children,
            'phonenumber': getattr(f, 'phoneareacode', '') + ' ' + getattr(f, 'phonenumber', ''),
        }
    
    
    def _registrations(self, reg_list):
        signed_in = []
        signed_out = []
    
        if 'records' in reg_list:
            # Yes: get the names of the kids
            for reg in reg_list.records:
                # Get the name/status of each person
                if reg.stage == 'Signed-In':
                    signed_in.append( self._person(person_id=reg.primarypersonid) )
                elif reg.stage == 'Signed-Out':
                    signed_out.append( self._person(person_id=reg.primarypersonid) )
        return {'signed_in':signed_in, 'signed_out':signed_out}
        

    def _person_crm(self, person_id=None, tag_number=None, details=None):
        if person_id:
            where = "pers_personid=%s" % person_id
        elif tag_number:
            where = "pers_c_tag_number=%s" % tag_number
        else:
            return {'error': 'Person ID or Tag Number must be supplied for Person search.'}
        person_list = self.connection.client.service.query(where, "Person")
        p = person_list.records[0]
        record = {
            'name': u'%s %s' % (p.firstname, p.lastname),
            'personid': p.personid,
            'tagnumber': p.c_tag_number,
            'parentid': p.companyid,
        }
        
        # Deal with multi-select lists
        if getattr(p, 'c_medical_info', None):
            medical_info = p.c_medical_info.records
        else:
            medical_info = []
        
        # Add full details of the person, if requested.
        if details:
            f = self._parents(p.companyid)
            record.update({
                'parent': (getattr(f, 'c_salutation', '') + ' ' + f.name).strip(),
                'dob': p.c_dob.strftime('%d/%m%/%Y'),
                'group': getattr(f, 'c_kids_group', ''),
                'team': getattr(f, 'c_kids_team', ''),
                'school_year': p.c_school_year,
                'medical_info': medical_info,
                'medical_notes': getattr(p, 'c_medical_notes', ''),
            })        
        return record


    def _person(self, person_id=None, tag_number=None, details=None):
        if person_id:
            self.cursor.execute("SELECT * FROM person WHERE personid=%s", (person_id,))
        elif tag_number:
            self.cursor.execute("SELECT * FROM person WHERE tagnumber=%s", (tag_number,))
        else:
            return {'error': 'Person ID or Tag Number must be supplied for Person search.'}
            
        p = self.cursor.fetchone()
        if not p:
            return {'error': 'No records found for the tag.'}
        
        record = {
            'name': p['name'],
            'personid': p['personid'],
            'tagnumber': p['tagnumber'],
            'parentid': p['family_tag'],
        }
        
        # Deal with multi-select lists
        if p['medical_info']:
            medical_info = p['medical_info'].split(',')
        else:
            medical_info = []
        
        # Add full details of the person, if requested.
        if details:
            f = self._family(p['family_tag'])
            record.update({
                'parent': f.get('name', ''),
                'dob': p['dob'] and p['dob'].strftime('%d/%m%/%Y') or '',
                'group': p['kids_group'] or '',
                'team': p['kids_team'] or '',
                'school_year': p['school_year'],
                'medical_info': medical_info,
                'medical_notes': p['medical_notes'] or '',
            })
        return record        
        
    def _parents(self, company_id):
        family_list = self.connection.client.service.query("comp_companyid=%s" % company_id, "Company")
        return family_list.records[0]


class CRMPerson(SageCRMWrapper):
    TERRITORIES = {
        'Worldwide':47483640,
        'Active':-2147483638,
        'Inactive':-2147483639,
        'Kidswork':-89478504,
        'Kidswork Inactive':-89478505
    }

    def family(self, from_date):
        """
        Gets the family records from the CRM system that have changed since the from date.
        """
        # Make sure we are logged into the CRM system
        #self.crm_login()
        
        # Query the CRM system
        if not from_date:
            from_date = '1980-01-01 00:00:00'
        where = "comp_updateddate >='%s'" % from_date
        family_list = self.connection.client.service.query(where, "Company")
        
        if 'records' not in family_list:
            return []
        
        families = self._family_record(family_list)
        
        app.logger.debug(family_list.more)
        while family_list.more:    
            family_list = self.connection.client.service.next()
            next_list = self._family_record(family_list)
            families.extend(next_list)
            app.logger.debug(family_list.more)
    
        app.logger.debug('Fetched %d families' % len(families))
        return families


    def _family_record(self, family_list):
        families = []
        for f in family_list.records:
            name = getattr(f, 'c_salutation','') + ' ' + f.name

            record = {
                'familyid': f.companyid,
                'name': name.strip(),
                'tagnumber': getattr(f, 'c_familynumber', 0),
                'territory': f.secterr,
            }
            families.append(record)
        return families
        

    def person(self, from_date):
        """
        Get the updated person records from the CRM system.
        """
        # Query the CRM system
        if not from_date:
            from_date = '1980-01-01 00:00:00'
        where = "pers_updateddate >='%s'" % from_date       
        person_list = self.connection.client.service.query(where, "Person")
        
        if 'records' not in person_list:
            return []
        
        people = self._person_record(person_list)

        app.logger.debug(person_list.more)       
        while person_list.more:    
            person_list = self.connection.client.service.next()
            next_list = self._person_record(person_list)
            people.extend(next_list)
            app.logger.debug(person_list.more)
    
        app.logger.debug('Fetched %d people' % len(people))        
        return people


    def _person_record(self, person_list):
        people = []
        for p in person_list.records: 
            # Deal with multi-select lists
            if getattr(p, 'c_medical_info', None):
                medical_info = p.c_medical_info.records
            else:
                medical_info = []
                
            if getattr(p, 'c_teamserving', None):
                team_serving = p.c_teamserving.records
            else:
                team_serving = []
                
            # Get the family tag number for the parent
            if getattr(p, 'companyid', None):
                family_tag = self.family_tag(p.companyid)
            else:
                family_tag = 0
            
            # Handle the address records
            if 'records' in getattr(p, 'address', []):
                address = p.address.records[0]
                address1 = getattr(address, 'address1','')
                address2 = getattr(address, 'address2','')
                city = getattr(address, 'city','')
                postcode = getattr(address, 'postcode','')
                country = getattr(address, 'country','')
            else:
                address1 = ''
                address2 = ''
                city = ''
                postcode = ''
                country = ''
                
            # Handle the phone records
            home_phone = ''
            mobile_phone = ''
            if 'records' in getattr(p, 'phone', []):
                for ph in p.phone.records:
                    if ph.type=='Business':
                        home_phone = getattr(ph,'countrycode','') + getattr(ph,'areacode','') + getattr(ph,'number','')
                    elif ph.type=='Mobile':
                        mobile_phone = getattr(ph,'countrycode','') + getattr(ph,'areacode','') + getattr(ph,'number','')

            # Convert some date fields to Boolean
            if getattr(p, 'c_baptism', None):
                baptised = True
            else:
                baptised = False
            if getattr(p, 'c_firsttimecommitment', None):
                salvation = True
            else:
                salvation = False
                
            record = {
                'personid': p.personid,
                'name': u'%s %s' % (p.firstname, p.lastname),
                'type': getattr(p, 'c_type', ''),
                'family_tag': family_tag,
                'tagnumber': getattr(p, 'c_tag_number', 0),
                'kids_group': getattr(p, 'c_kids_group', ''),
                'kids_team': getattr(p, 'c_kids_team', ''),
                'school_year': getattr(p, 'c_school_year', 0),
                'dob': getattr(p, 'c_dob', None),
                'medical_info': ','.join(medical_info),
                'medical_notes': getattr(p, 'c_medical_notes', ''),
                'territory': p.secterr,
                'firstname': getattr(p, 'firstname',''),
                'gender': getattr(p, 'gender',''),
                'marital_status': getattr(p, 'c_maritalstatus',''),
                'lifegroup': getattr(p, 'c_caregroup',''),
                'address1': address1,
                'address2': address2,
                'city': city,
                'postcode': postcode,
                'country': country,
                'home_phone': home_phone,
                'mobile_phone': mobile_phone,
                'email': getattr(p, 'emailaddress',''),
                'team_serving': team_serving,
                'baptised': baptised,
                'salvation': salvation,
            }
            people.append(record)
        return people    


    def team_serving_options(self, from_date):
        # Query the CRM system and get all current team-serving groups
        if not from_date:
            from_date = '1980-01-01 00:00:00'
        where = "capt_family='pers_c_teamserving'"
        #where = "capt_family='pers_c_teamserving' and capt_updateddate>='%s'" % from_date
        option_list = self.connection.client.service.query(where, "Custom_Captions")
        if 'records' not in option_list:
            return []
        
        records = []
        for o in option_list.records:
            record = {
                'groupsid': o.captionid,
                'code': o.code,
                'name': o.uk
            }
            records.append( record )
        return records
        
    def family_tag(self, familyid):
        """
        Get the family tag from the local database using the family ID.
        """
        sql = "SELECT tagnumber FROM family WHERE familyid=%s"
        self.cursor.execute(sql, (familyid,))
        f = self.cursor.fetchone()

        if not f:
            return 0
        else:
            return f.get('tagnumber', 0)

    def registrations(self, from_date):
        """
        Push the registrations from the current date to CRM.
        """
        if not from_date:
            from_date = '1980-01-01 00:00:00'

        # Get the registrations from the local db
        sql = """
            select f.familyid, p.personid, r.* from registration r
            inner join family f on f.tagnumber=family_tag
            inner join person p on p.tagnumber=person_tag
            where event_date>=%s
        """
        self.cursor.execute(sql, (from_date,))
        rows = self.cursor.fetchall()
        
        if not rows:
            return
            
        # Push the records to CRM
        for r in rows:
            self._register_crm(r['familyid'], r['family_tag'], r['personid'], r['eventid'], r['event_date'].strftime('%Y-%m-%d'), r['status'])
 
 
    def _register_crm(self, familyid, family_tag, personid, event_id, event_date, status):
        oppo_opened = event_date + 'T00:00:00'
        oppo_targetclose = event_date + 'T23:59:59'
           
        # Set the certainty based on the status
        if status=='Signed-Out':
            certainty = 100
            oppo_stage = status
            oppo_status = 'Won'
        else:
            certainty = 50
            oppo_stage = status
            oppo_status = 'In Progress'
                
        # Check if the registration (Opportunity) record exists
        where = "oppo_primarypersonid=%s and oppo_customerref='%s' and oppo_c_eventid=%s and oppo_opened>='%s 00:00:00' and oppo_opened<='%s 23:59:59'" % (personid, family_tag, event_id, event_date, event_date)
        reg_list = self.connection.client.service.query(where, "Opportunity")
        if 'records' in reg_list:
            # Update the existing record
            o = reg_list.records[0]
            oppo = self.connection.client.factory.create("opportunity")
            oppo.opportunityid = o.opportunityid
            oppo.stage = oppo_stage
            oppo.status = oppo_status
            oppo.certainty = certainty
            self.connection.client.service.update("opportunity", [oppo])
        else:
            # Add a new registration
            oppo = self._opportunity_defaults()
            oppo.primarycompanyid = familyid
            oppo.customerref = family_tag
            oppo.primarypersonid = personid
            oppo.c_eventid = event_id
            oppo.stage = oppo_stage
            oppo.status = oppo_status
            oppo.certainty = certainty
            oppo.opened = oppo_opened
            oppo.targetclose = oppo_targetclose
            self.connection.client.service.add("opportunity", [oppo])
   
    
    def person_membership(self, personid, group_name, add_action=True):
        """
        Add or remove a 'team-serving' membership for a person.
        """
        # Get the current memberships for the Person
        where = "pers_personid =%s" % personid     
        person_list = self.connection.client.service.query(where, "Person")
        if 'records' not in person_list:
            return {'response':'Failed', 'message':'Cannot find person with the given ID'}
        
        person = person_list.records[0]        
        if getattr(person, 'c_teamserving', None):
            team_serving = person.c_teamserving.records
        else:
            # No memberships for the person
            team_serving = []
                
        # Add/remove the group if it's there
        if add_action:
            # Add the group if it is not there
            if group_name not in team_serving:
                team_serving.append( group_name )
                p = self.connection.client.factory.create("person")
                p.personid = personid
                p.c_teamserving = self.connection.client.factory.create("multiselectfield")
                p.c_teamserving.multiselectfieldname = 'c_teamserving'
                p.c_teamserving.records = team_serving
                result = self.connection.client.service.update("person", [p])
        else:
            # Remove the group if it is there
            if group_name in team_serving:
                team_serving.remove(group_name)
                p = self.connection.client.factory.create("person")
                p.personid = personid
                p.c_teamserving = self.connection.client.factory.create("multiselectfield")
                p.c_teamserving.multiselectfieldname = 'c_teamserving'
                p.c_teamserving.records = team_serving
                result = self.connection.client.service.update("person", [p])
            
        return {'response':'Success'}
        
 
    def _opportunity_defaults(self):
        oppo = self.connection.client.factory.create("opportunity")
        oppo.secterr = 'Kidswork'
        oppo.status = 'In Progress'
        oppo.currency = 3
        oppo.forecast_cid = 3
        oppo.totalquotes_cid = 3
        oppo.totalorders_cid = 3
        oppo.assigneduserid = 1
        oppo.source = 'Kidswork App'
        return oppo
      