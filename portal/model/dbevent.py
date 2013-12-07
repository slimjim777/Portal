from portal.model.models import Database

__author__ = 'jjesudason'


class Event(Database):

    def get_events(self):
        """
        Get the Kids Work events from the local database.
        """
        self.cursor.execute("SELECT * FROM event WHERE type='Kidswork'")

        event_list = []
        for e in self.cursor:
            event_list.append({
                'event_id': e['eventid'],
                'name': e['name'],
            })

        return event_list
