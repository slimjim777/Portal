import suds.client


# To enable debugging of the SOAP messages
#import logging
#logging.basicConfig(level=logging.INFO)
#logging.getLogger('suds.client').setLevel(logging.DEBUG)
#logging.getLogger('suds.transport').setLevel(logging.DEBUG)

MESSAGE_LOGON = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><logon xmlns="http://tempuri.org/type"><username>%s</username><password>%s</password></logon></soap:Body></soap:Envelope>'
MESSAGE_QUERY = '<?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><query xmlns="http://tempuri.org/type"><queryString>%s</queryString><entityname>%s</entityname></query></soap:Body></soap:Envelope>'

"""
            add(xs:string entityname, ewarebase[] records, )
            addrecord(xs:string entityname, ewarebase[] records, )
            addresource(xs:string entityname, ewarebase[] records, )
            altercolumnwidth(xs:string entityname, xs:string columnname, xs:string width, )
            delete(xs:string entityname, ewarebase[] records, )
            getallmetadata()
            getdropdownvalues(xs:string entityname, )
            getmetadata(xs:string entityname, )
            getversionstring()
            logoff(xs:string sessionId, )
            logon(xs:string username, xs:string password, )
            next()
            nextqueryrecord()
            query(xs:string queryString, xs:string entityname, )
            queryentity(xs:int id, xs:string entityname, )
            queryid(xs:string queryString, xs:string entityname, xs:string orderby, xs:dateTime journaltoken, xs:boolean showdeletedrecords, )
            queryidnodate(xs:string queryString, xs:string entityname, xs:boolean showdeletedrecords, )
            queryrecord(xs:string fieldlist, xs:string queryString, xs:string entityname, xs:string orderby, )
            update(xs:string entityname, ewarebase[] records, )
            updaterecord(xs:string entityname, ewarebase[] records, )
"""


class Connection(object):

    def __init__(self, wsdl):
        self.client = suds.client.Client(wsdl)
        self.client.options.cache.clear()

    def login(self, username, password):
        self.auth = self.client.service.logon(__inject={'msg':MESSAGE_LOGON % (username, password)})
        
        # Store the sessionId in the header
        sessionHeader = self.client.factory.create("SessionHeader")
        sessionHeader.sessionId = self.auth["sessionid"]
        self.client.set_options(soapheaders={"SessionHeader":sessionHeader})
    
    def add(self, entityname, records):
        return self.client.service.add(entityname, records)
        
    def addrecord(self, entityname, records):
        return self.client.service.addrecord(entityname, records)
 
    def update(self, entityname, records):
        return self.client.service.update(entityname, records)
        
    def updaterecord(self, entityname, records):
        return self.client.service.updaterecord(entityname, records)
        
    def delete(self, entityname, records):
        return self.client.service.delete(entityname, records)

    def query(self, where, entityname):
        #return self.client.service.query(__inject={'msg':MESSAGE_QUERY % (where, entityname)})
        return self.client.service.query(where, entityname)
    
    def next(self):
        return self.client.service.next()
            
    
    