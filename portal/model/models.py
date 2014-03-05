# -*- coding: utf-8 -*-
import urlparse

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

