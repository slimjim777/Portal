import datetime
from flask import session
from portal.model.models import Database

__author__ = 'jjesudason'


class Person(Database):

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
        if len(group_names) > 0:
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
            order by name
        """
        people = []
        self.cursor.execute(sql, (names,territories,))
        rows = self.cursor.fetchall()

        if not rows:
            return []

        for r in rows:
            people.append(dict(r))

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
            if p['status'] == 'Signed-In':
                signed_in.append(person)
            elif p['status'] == 'Signed-Out':
                signed_in.append(person)

        return {'signed_in':signed_in, 'signed_out':signed_out}

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
            select g.name, g.code from membership m
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
            select g.name, g.code from groups g
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

        return {'team_serving': groups, 'team_serving_not': groups_not}

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
                sql = "INSERT INTO registration (person_tag, family_tag, eventid, event_date, status) VALUES (%s,%s,%s,%s,%s)"
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
                    'school_year': c['school_year'],
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
        return record

    def _registrations(self, reg_list):
        signed_in = []
        signed_out = []

        if 'records' in reg_list:
            # Yes: get the names of the kids
            for reg in reg_list.records:
                # Get the name/status of each person
                if reg.stage == 'Signed-In':
                    signed_in.append(self._person(person_id=reg.primarypersonid))
                elif reg.stage == 'Signed-Out':
                    signed_out.append(self._person(person_id=reg.primarypersonid))
        return {'signed_in':signed_in, 'signed_out':signed_out}

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
                'dob': p['dob'] and p['dob'].strftime('%d/%m/%Y') or '',
                'group': p['kids_group'] or '',
                'team': p['kids_team'] or '',
                'school_year': p['school_year'],
                'medical_info': medical_info,
                'medical_notes': p['medical_notes'] or '',
            })
        return record

    def registrations_sync(self, from_date):
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
        return rows
