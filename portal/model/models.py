# -*- coding: utf-8 -*-
from portal.model.sagecrm import Connection
from portal import app
import psycopg2
import os, datetime
import urlparse
import bcrypt


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

    def __init__(self):
        db = Database()
        self.sqlconn = db.sqlconn
        
    def _hashed(self, pwd):
        return bcrypt.hashpw(pwd, os.environ["SALT"])

    def login(self, username, password):
        """
        Verify the user login details.
        """
        self.cursor.execute("SELECT * FROM Visitor WHERE username=? AND password=?", (username, self._hashed(password)))
        row = self.cursor.fetchone()
        self.sqlconn.close()
        
        if row:
            return {
                    'personid': row[0],
                    'username': row[2],
                    'name': row[3],
                    'access': row[4]
                    }
        else:
            return None


class SageCRMWrapper(object):
    def __init__(self):
        self.connection = Connection(app.config['SAGE_WSDL'])
        self.connection.login( app.config['SAGE_USER'], app.config['SAGE_PASSWORD'] )
        
        db = Database()
        self.sqlconn = db.sqlconn
        

class Event(SageCRMWrapper):
     def get_events(self):
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
        

class Person(SageCRMWrapper):
    
    def family(self, family_number, event_id):
        """
        Get the check to see if any children are signed-in for this tag.
        """
        # Get the family record for details
        family_record = self._family(family_number)

        # Check for event registrations for this date
        today = datetime.date.today().isoformat()
        where = "oppo_customerref='%s' and oppo_c_eventid=%s and oppo_opened>='%s 00:00:00' and oppo_opened<='%s 23:59:59'" % (family_number, event_id, today, today)
        app.logger.debug(where)

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
            app.logger.debug(p)
            record.update(p)
            
            records.append(record)
        
        app.logger.debug(records)
        return records


    def scan(self, tag):
        """
        Get the details of the person/family from the tag.
        """
        prefix = tag[0:1]
        tag_number = tag[1:]
        print "---",tag, prefix, tag_number
        
        if prefix == 'F': 
            record = self._family(tag_number)
        elif prefix == 'C':
            record = self._person(tag_number=tag_number, details=True)
            
        return record


    def _register(self, family_number, people, event_id, stage, status):
        today = datetime.date.today().isoformat()
        for p in people:
            # Get the person record details for this child's tag number
            pers = self._person(tag_number=p)
            
            # Set the certainty based on the status
            if status=='Won':
                certainty = 100
            else:
                certainty = 50
                    
            # Check if the registration (Opportunity) record exists
            where = "oppo_primarypersonid=%s and oppo_customerref='%s' and oppo_c_eventid=%s and oppo_opened>='%s 00:00:00' and oppo_opened<='%s 23:59:59'" % (pers['personid'], family_number, event_id, today, today)
            reg_list = self.connection.client.service.query(where, "Opportunity")
            app.logger.debug(where)
            app.logger.debug(reg_list)
            if 'records' in reg_list:
                # Update the existing record
                o = reg_list.records[0]
                oppo = self.connection.client.factory.create("opportunity")
                oppo.opportunityid = o.opportunityid
                oppo.stage = stage
                oppo.status = status
                oppo.certainty = certainty
                self.connection.client.service.update("opportunity", [oppo])
            else:
                # Add a new registration
                app.logger.debug(family_number)
                oppo = self._opportunity_defaults()
                oppo.primarycompanyid = pers['parentid']
                oppo.customerref = family_number
                oppo.primarypersonid = pers['personid']
                oppo.c_eventid = event_id
                oppo.stage = stage
                oppo.status = status
                oppo.certainty = certainty
                self.connection.client.service.add("opportunity", [oppo])
                
        return {"result":"success"}


    def _opportunity_defaults(self):
        oppo = self.connection.client.factory.create("opportunity")
        oppo.opened = datetime.datetime.now().isoformat('T')
        oppo.targetclose = datetime.datetime.now().isoformat('T')
        oppo.secterr = 'Kidswork'
        oppo.status = 'In Progress'
        oppo.currency = 3
        oppo.forecast_cid = 3
        oppo.totalquotes_cid = 3
        oppo.totalorders_cid = 3
        oppo.assigneduserid = 1
        oppo.source = 'Kidswork App'
        return oppo
    
        
    def _family(self, family_number):
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
        

    def _person(self, person_id=None, tag_number=None, details=None):
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
        app.logger.debug(p)
        return record
        
        
    def _parents(self, company_id):
        family_list = self.connection.client.service.query("comp_companyid=%s" % company_id, "Company")
        return family_list.records[0]


