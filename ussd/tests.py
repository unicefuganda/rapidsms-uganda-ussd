from django.test.testcases import TestCase
from django.test.client import Client

from rapidsms_xforms.models import XForm
from ussd.models import USSDSession, MenuItem


# view tests
class UssdTestCase(TestCase):
    def setUp(self):
        self.menu_items = MenuItem.
        self.ussd_session = USSDSession.objects.create(transaction_id='1',connection='1234567',\
                                                       ussd_request_string='hello rapidsms',current)
        #self.client = Client()
        c = Client()
        #s = self.client.session
        response = c.post('ussd/')
        self.assertEqual(response.status_code,302)
