from portal import app
from portal.model.dbperson import Person
from portal.model.models import SageCRMWrapper

__author__ = 'jjesudason'


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

    @staticmethod
    def _family_record(family_list):
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

    @staticmethod
    def _person_record(person_list):
        db_person = Person()
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
                family_tag = db_person.family_tag(p.companyid)
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
                    if ph.type == 'Business':
                        home_phone = getattr(ph,'countrycode','') + getattr(ph,'areacode','') + getattr(ph,'number','')
                    elif ph.type == 'Mobile':
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
            partner = getattr(p, 'c_partner', False)
            key_leader = getattr(p, 'c_key_leader', False)
    
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
                'partner': partner,
                'key_leader': key_leader,
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

    def registrations_sync(self, rows):
        """
        Push the registrations from the current date to CRM.
        """
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

    def person_update(self, personid, field, field_value):
        """
        Update the boolean flags on the person.
        """
        p = self.connection.client.factory.create("person")
        p.personid = personid
        if field == 'partner':
            p.c_partner = field_value
        elif field == 'key_leader':
            p.c_key_leader = field_value
        else:
            return {'response':'Failed', 'message':'Invalid field provided for the update'}
        
        result = self.connection.client.service.update("person", [p])
        return {'response':'Success'}

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

        # Check that the group still exists in SageCRM
        # ...have to do this or web services will create spurious groups
        where = "capt_family='pers_c_teamserving' and convert(nvarchar(max),capt_uk)='%s'" % group_name
        option_list = self.connection.client.service.query(where, "Custom_Captions")
        if 'records' not in option_list:
            return {'response':'Failed', 'message':'This group has been deleted from the CRM system'}

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
