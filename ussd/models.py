from django.db import models
from mptt.models import MPTTModel
from rapidsms.models import Contact, Connection
from rapidsms_xforms.models import XForm
import mptt

class USSDSession(models.Model):
    """Model to hold session information"""

    #a unique session identifier which is maintained for an entire USSD session/transaction
    transaction_id = models.CharField(max_length=100)

    #The telephone number of the subscriber interacting with the USSD code
    # match this with 'msisdn'
    connection = models.ForeignKey(Connection)

    #The number that the subscriber dialed.
    # for example: *100#, 100 is the service code
    ussd_service_code = models.CharField(max_length=4)

    #The information that the subscriber inputs to the system.
    ussd_request_string = models.CharField(max_length=100)

    current_menu_item = models.ForeignKey('MenuItem', null=True)
    current_xform = models.ForeignKey(XForm, null=True)

    #create XForm models and preferably fk to that.
    xform_step = models.IntegerField()


class MenuItem(MPTTModel):
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    label = models.CharField(max_length=50)
    xform = models.ForeignKey(XForm, null=True)
    #not sure of what type order should be associated to
    #TODO fk order to something similar to ScriptStep orders
    order = models.IntegerField()



