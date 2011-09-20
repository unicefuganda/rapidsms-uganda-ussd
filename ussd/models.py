from django.db import models
from rapidsms.models import Contact, Connection


class USSDSession(models.Model):
    """Model to hold session information"""

    #a unique session identifier which is maintained for an entire USSD session/transaction
    transactionId  = models.CharField(max_length=100)

    #the time the USSD request came in
    transactionTime = models.DateTimeField()

    #The telephone number of the subscriber interacting with the USSD code
    msisdn = models.ForeignKey(Connection)

    #The number that the subscriber dialed.
    # for example: *100#, 100 is the service code
    ussdServiceCode = models.CharField(max_length=4)

    #The information that the subscriber inputs to the system.
    ussdRequestString = models.CharField(max_length=100)

    # This indicates whether the incoming request is a a response to
    # a previously open request. Two values are possible: true/false
    #TODO data type for response is a little vague; booleans would do well here, need to confirm.
    response  = models.IntegerField()

    def __unicode__(self):
        #for now, we return msisdn for str() of USSDSession objects
        return self.msisdn