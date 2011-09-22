from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.conf import settings
import urllib
from rapidsms_xforms.models import XForm
from rapidsms.models import Connection, Backend, Contact
from ussd.models import USSDSession, MenuItem


class UssdTestCase(TestCase):
    def setUp(self):
        menu_item = MenuItem.objects.create(
        label="Welcome to RapidSMS Uganda. We would like you to answer some great questions. Please select choice",
            xform=None,
            order=1
        )
        ussd_backend = Backend.objects.create(name="ussd")
        ussdd_contact = Contact.objects.create(name="Victor Miclovich")
        ussd_connection = Connection.objects.create(backend=ussd_backend, identity="someId", contact=ussdd_contact)
        ussd_session = USSDSession.objects.create(
           #probably setup by us or the USSD gateway
           transaction_id='1', \
           #reusing existing connection
           connection=ussd_connection, \
           #user will probably make a choice between 1 or n
           ussd_request_string='1', \
           current_menu_item=menu_item, \
           #setting xform Node to None
           current_xform=None, \
           submission=None, \
           xform_step=1, \
       )

    def testContacts(self):
        """This tests the existence of a contact record"""
        c = Contact.objects.get(name="Victor Miclovich")
        u_session = USSDSession.objects.get(transaction_id='1')
        self.assertEquals(u_session.connection.contact, c)

