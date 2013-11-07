# -*- coding: utf-8 -*-
import urlparse

from portal.model.sagecrm import Connection
import psycopg2
import psycopg2.extras
import os


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
        self.cursor = self.sqlconn.cursor(cursor_factory=psycopg2.extras.DictCursor)



class SageCRMWrapper(object):
    def __init__(self):
        self.connection = None

    def crm_login(self):
        self.connection = Connection(os.environ['SAGE_WSDL'])
        self.connection.login( os.environ['SAGE_USER'], os.environ['SAGE_PASSWORD'] )


