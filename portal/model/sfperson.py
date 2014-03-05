from simple_salesforce import Salesforce
import os
from portal import app


class SFPerson(object):
    def __init__(self):
        self.login()

    def login(self):
        self.connection = Salesforce(
            username=os.environ['SF_USERNAME'],
            password=os.environ['SF_PASSWORD'],
            security_token=os.environ['SF_TOKEN'],
            sandbox=False
        )

    def registrations_sync(self, rows):
        """
        Push the registrations from the current date to CRM.
        """
        if not rows:
            return

        # Push the records to CRM
        for r in rows:
            sf_record = {
                'Contact__c': r['contactid'],
                'Event__c': r['externalid'],
                'Event_Date__c': r['event_date'].strftime('%Y-%m-%d'),
                'Status__c': r['status'],
            }
            app.logger.debug(sf_record)

            self.connection.Registration__c.upsert('ExternalId__c/%d' % r['registrationid'], sf_record)

    def person(self, from_date):
        """
        Get the updated person records from the CRM system.
        """
        # Query the CRM system
        if not from_date:
            from_string = '1980-01-01T00:00:00Z'
        else:
            from_string = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        soql = """
            SELECT Id, Firstname, Lastname, Child_Tag_Number__c, Account.Family_Tag__c, ExternalId__c,School_Year__c,
                Contact_Type__c, Kids_Group__c, Kids_Team__c, Birthdate, Medical_Info__c, Medical_Notes__c, Active__c,
                RecordType.Name, Gender__c, Marital_Status__c, MailingStreet, MailingCity, MailingPostalCode,
                MailingCountry, Phone, MobilePhone, Email, IsBaptised__c, Salvation__c, Partner__c, isKeyLeader__c
            FROM Contact
            WHERE LastModifiedDate >= %s
        """ % from_string

        result = self.connection.query_all(soql)
        records = []
        for r in result.get('records', []):
            address_lines = (r['MailingStreet'] or '').split('\n')

            rec = {
                'name': ('%s %s' % (r['FirstName'], r['LastName'])).strip(),
                'family_tag': int(r['Account']['Family_Tag__c']) if r['Account']['Family_Tag__c'] else None,
                'tagnumber': r['Child_Tag_Number__c'],
                'type': r['Contact_Type__c'],
                'kids_group': r['Kids_Group__c'],
                'kids_team': r['Kids_Team__c'],
                'school_year': int(r['School_Year__c']) if r['School_Year__c'] else None,
                'dob': r['Birthdate'],
                'medical_info': r['Medical_Info__c'],
                'medical_notes': r['Medical_Notes__c'],
                'territory': r['RecordType']['Name'],
                'firstname': r['FirstName'],
                'gender': r['Gender__c'],
                'marital_status': r['Marital_Status__c'],
                'lifegroup': None,
                'address1': address_lines[0],
                'address2': address_lines[1] if len(address_lines) > 1 else None,
                'city': r['MailingCity'],
                'postcode': r['MailingPostalCode'],
                'country': r['MailingCountry'],
                'home_phone': r['Phone'],
                'mobile_phone': r['MobilePhone'],
                'email': r['Email'],
                'baptised': r['IsBaptised__c'],
                'salvation': r['Salvation__c'],
                'partner': r['Partner__c'],
                'key_leader': r['isKeyLeader__c'],
                'personid': r['ExternalId__c'],
                'externalid': r['Id'],
            }
            if not r['Active__c']:
                rec['territory'] = 'Inactive'
            records.append(rec)

        return records

    def family(self, from_date):
        """
        Gets the family records from the CRM system that have changed since the from date.
        """
        # Query the CRM system
        if not from_date:
            from_string = '1980-01-01T00:00:00Z'
        else:
            from_string = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        soql = """
            SELECT Id, Name, Salutation__c, Family_Tag__c, ExternalId__c, Active__c
            FROM Account
            WHERE LastModifiedDate >= %s
        """ % from_string

        result = self.connection.query_all(soql)
        records = []
        for r in result.get('records', []):
            rec = {
                'name': '%s %s'.strip() % (r['Salutation__c'] or '', r['Name']),
                'family_tag': int(r['Family_Tag__c']) if r['Family_Tag__c'] else None,
                'tagnumber': r['Family_Tag__c'],
                'territory': 'Kidswork' if r['Family_Tag__c'] else 'Congregation',
                'familyid': r['ExternalId__c'],
                'externalid': r['Id'],
            }
            if not r['Active__c']:
                rec['territory'] = 'Inactive'
            records.append(rec)

        return records

    def team_serving_options(self, from_date):
        """
        Query the CRM system and get all current team-serving groups
        """
        # Query the CRM system
        if not from_date:
            from_string = '1980-01-01T00:00:00Z'
        else:
            from_string = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        soql = """
            SELECT Id, Name, ExternalId__c, IsActive__c
            FROM Team__c
            WHERE LastModifiedDate >= %s and IsActive__c = true
        """ % from_string

        result = self.connection.query_all(soql)
        records = []
        for r in result.get('records', []):
            rec = {
                'name': r['Name'],
                'groupsid': r['ExternalId__c'],
                'code': r['Id'],
            }
            records.append(rec)

        return records

    def person_membership(self, contact_id, group_code, membershipid, add_action=True):
        """
        Add or remove a 'team-serving' membership for a person.
        """
        sf_record = {
            'Contact__c': contact_id,
            'Team__c': group_code,
        }
        if add_action:
            sf_record['ExternalId__c'] = membershipid

        # Get the ID of the membership record
        soql = "select Id from ContactTeamLink__c where Contact__c='%s' and Team__c='%s'" % (contact_id, group_code)
        result = self.connection.query(soql)
        if len(result.get('records', [])) == 0:
            sf_link_id = None
        else:
            sf_link_id = result.get('records')[0]['Id']

        if add_action and sf_link_id:
            # Update the record
            self.connection.ContactTeamLink__c.update(sf_link_id, sf_record)
        elif add_action and not sf_link_id:
            # Create a membership link
            self.connection.ContactTeamLink__c.create(sf_record)
        elif not add_action and sf_link_id:
            # Delete the record
            self.connection.ContactTeamLink__c.delete(sf_link_id)

        return {'response': 'Success', 'membership_id': sf_link_id}

    def person_update(self, personid, externalid, field, field_value):
        """
        Update the boolean flags on the person.
        """
        sf_record = {
            'ExternalId__c': personid,
        }
        if field == 'partner':
            sf_record['Partner__c'] = field_value
        elif field == 'key_leader':
            sf_record['isKeyLeader__c'] = field_value
        else:
            return {'response': 'Failed', 'message': 'Invalid field provided for the update'}

        self.connection.Contact.update(externalid, sf_record)
        return {'response': 'Success'}
