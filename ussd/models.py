from django.db import models
from rapidsms.models import Contact, Connection
import mptt

class USSDSession(models.Model):
    """Model to hold session information"""

    #a unique session identifier which is maintained for an entire USSD session/transaction
    transaction_id  = models.CharField(max_length=100)

    #The telephone number of the subscriber interacting with the USSD code
	# match this with 'msisdn'
    connection = models.ForeignKey(Connection)

    #The number that the subscriber dialed.
    # for example: *100#, 100 is the service code
    ussd_service_code = models.CharField(max_length=4)

    #The information that the subscriber inputs to the system.
    ussd_request_string = models.CharField(max_length=100)
	
	#create XForm models and preferably fk to that.
	xform_step = models.IntegerField()

class MenuItem(models.Model):
	parent = models.ForeignKey('self',null=True,blank=True,related_name='children')
	label = models.CharField(max_length=50)
	#xform_
	#not sure of what type order should be associated to
	#TODO fk order to something similar to ScriptStep orders
	order = models.IntegerField()


# register with mptt
# when properly implemented, calls to 
# menu Item placeholders is made heirarchical by order
mptt.register(MenuItem,order_insertion_by=['order'])	
	