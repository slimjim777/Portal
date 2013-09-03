import psycopg2
import psycopg2.extras
from portal.model.models import Database
from portal.model.models import CRMPerson, Person
import gevent
import time, random
from portal import app


FAMILY = ['name','tagnumber']
PERSON = ['name','family_tag','tagnumber','type','kids_group','kids_team','school_year','dob','medical_info','medical_notes']



class SyncCRM(object):

    def __init__(self):
        db = Database()
        self.sqlconn = db.sqlconn
        self.cursor = self.sqlconn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        

    def lastsync(self):
        self.cursor.execute("select * from sync")
        rows = []
        for r in self.cursor:
            rec = {
                'syncid': r['syncid'],
                'tablename': r['tablename'],
                'lastsync': r['lastsync'],
            }
            rows.append(rec)
            
        return rows
        
        
    def update_lastsync(self, tablename, sync_date):
        self.cursor.execute('UPDATE sync SET lastsync=%s WHERE tablename=%s', (sync_date,tablename))
        self.sqlconn.commit()
        
    
    def upsert(self, entity, records):
        """
        Update of insert the record to the database. The full record is expected.
        """
        if isinstance(records, dict):
            records = [records]
        
        if entity == 'family':
            fields = FAMILY
        elif entity == 'person':
            fields = PERSON
        else:
            return {'error': 'Unknown entity'}
    
        
    def start_sync(self):
        gevent.spawn(self.run_sync)
        return {'sync':'Started'}


    def run_sync(self):        
        dates = self.lastsync()
        self.crm = CRMPerson()
        self.crm.crm_login()
        
        for d in dates:
            getattr(self, d['tablename']+'_sync')( d['lastsync'] )
        
        app.logger.info('Sync done')
    

    def family_sync(self, from_date):
        """
        Sync the updated family records from the CRM system.
        """
        app.logger.info('Family sync')
        # Store the date/time
        sync_start = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get the updated records from CRM
        families = self.crm.family(from_date)
        
        # Upsert the records into the Database
        db = Person()
        app.logger.info('Upsert the family records')
        for f in families:
            db.family_upsert(f)
        
        # Update the last sync date
        self.update_lastsync('family', sync_start)
        
        # Remove inactive records from local db
        self.remove_inactive(['family'])

        app.logger.info('Family sync done')

        
    def person_sync(self, from_date):
        app.logger.info('Person sync')
        # Store the date/time
        sync_start = time.strftime('%Y-%m-%d %H:%M:%S')

        # Get the updated records from CRM
        records = self.crm.person(from_date)

        # Upsert the records into the Database
        db = Person()
        app.logger.info('Upsert the person records')
        for r in records:
            db.person_upsert(r)

        # Update the last sync date
        self.update_lastsync('person', sync_start)

        # Remove inactive records from local db
        self.remove_inactive(['person'])
        
        app.logger.info('Person sync done')
        
    
    def remove_inactive(self, types=['family', 'person']):
        """
        Remove inactive records from the database.
        """
        app.logger.info('Remove inactive records')
        sql = "DELETE FROM %s WHERE territory like '%%Inactive%%'"
        
        for t in types:
            s = sql % t
            self.cursor.execute(s)
            self.sqlconn.commit()
        app.logger.info('Remove inactive records done')
            