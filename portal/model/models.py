# -*- coding: utf-8 -*-
from portal.model.sagecrm import Connection
from portal import app
import psycopg2
import psycopg2.extras
import os, datetime
import urlparse
import hashlib

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
        self.cursor = self.sqlconn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
    def _hashed(self, pwd):
        return hashlib.sha224(os.environ["SALT"] + pwd).hexdigest()

    def login(self, username, password):
        """
        Verify the user login details.
        """
        self.cursor.execute("SELECT * FROM Visitor WHERE username=%s AND password=%s", (username, self._hashed(password)))
        row = self.cursor.fetchone()
        #self.sqlconn.close()
        
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
            home_phone=%(home_phone)s, mobile_phone=%(mobile_phone)s, email=%(email)s
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
                %(postcode)s,%(country)s,%(home_phone)s,%(mobile_phone)s,%(email)s
                )"""
            self.cursor.execute(sql_insert, record)
            self.sqlconn.commit()
            
        return True    
      
        
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


    def _register_crm(self, family_number, people, event_id, stage, status):
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
        #where = "comp_updateddate >='%s' and comp_secterr<>%s" % (from_date, self.TERRITORIES['Worldwide']) 
        where = "comp_updateddate >='%s'" % from_date
        app.logger.debug(where)      
        family_list = self.connection.client.service.query(where, "Company")
        
        if 'records' not in family_list:
            return []
        
        families = self._family_record(family_list)
        
        app.logger.debug(family_list.more)
        while family_list.more:    
            family_list = self.connection.client.service.next()
            next_list = self._family_record(family_list)
            families.append(next_list)
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
        # Make sure we are logged into the CRM system
        #self.crm_login()

        # Query the CRM system
        if not from_date:
            from_date = '1980-01-01 00:00:00'
        where = "pers_updateddate >='%s' and pers_secterr<>%s" % (from_date, self.TERRITORIES['Worldwide'])       
        person_list = self.connection.client.service.query(where, "Person")
        
        if 'records' not in person_list:
            return []
        
        people = self._person_record(person_list)
        app.logger.debug(person_list.more)
        
        while person_list.more:    
            person_list = self.connection.client.service.next()
            app.logger.debug(person_list)
            if isinstance(person_list, list):
                next_list = self._person_record(person_list)
                people.append(next_list)
                app.logger.debug(person_list.more)
            else:
                break
    
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
                
            # Get the family tag number for the parent
            if getattr(p, 'companyid', None):
                f = self.family_by_id(p.companyid)
                if not f:
                    family_tag = 0
                else:
                    family_tag = getattr(f, 'c_familynumber', 0)
            
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
            }
            people.append(record)
        return people    
            
        
    def family_by_id(self, familyid):
        """
        Get the family record from CRM using it's ID.
        """
        # Make sure we are logged into the CRM system
        if not self.connection:
            self.crm_login()

        # Query the CRM system
        where = "comp_companyid=%s" % familyid      
        record_list = self.connection.client.service.query(where, "Company")

        if 'records' not in record_list:
            return None
        else:
            return record_list.records[0]
            
            
        