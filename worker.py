#!/usr/bin/env python
from portal.model.crmperson import CRMPerson
from portal.model.dbperson import Person
from portal.model.synccrm import SyncCRM

sync = SyncCRM()
sync.run_sync()
