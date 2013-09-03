#!/usr/bin/env python
from portal.model.synccrm import SyncCRM
from portal.model.models import CRMPerson
from portal.model.models import Person

sync = SyncCRM()
sync.run_sync()
