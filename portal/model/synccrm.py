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
        
        for d in dates:
            getattr(self, d['tablename']+'_sync')(d['lastsync'])
        
        app.logger.info('Task done')
    

    def family_sync(self, from_date):
        """
        Sync the updated family records from the CRM system.
        """
        # Store the date/time
        sync_start = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Get the updated records from CRM
        crm = CRMPerson()
        families = crm.family(from_date)
        app.logger.debug(families)
        
        # Upsert the records into the Database
        db = Person()
        for f in families:
            db.family_upsert(f)
        
        # Update the last sync date

        app.logger.info('Family sync')
        
    def person_sync(self, from_date):
        time.sleep(3)
        app.logger.info('Person sync')
        
        
        