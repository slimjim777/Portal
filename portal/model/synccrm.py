import psycopg2
import psycopg2.extras
from portal.model.models import Database


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
        
        