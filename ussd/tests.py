from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.conf import settings
from .models import MenuItem, USSDSession
import urllib
from rapidsms_xforms.models import XForm
from ussd.models import USSDSession, MenuItem

class BasicTest(TestCase):

    def setUp(self):
        self.old_router_url = getattr(settings, 'ROUTER_URL', None)
        settings.ROUTER_URL = None

    def tearDown(self):
        settings.ROUTER_URL = self.old_router_url

    def testNoExplosions(self):
        client = Client()
        # No menu in the DB, this should still return something
        url = reverse('ussd.views.ussd')
        print "url is %s" % url
        response = client.get(reverse('ussd.views.ussd'), {\
            'transactionId':'foo', \
            'transactionTime':'20110101(T)01:01:01',
            'msisdn':'078675309',
            'ussdServiceCode':'300',
            'ussdRequestString':'',
        })
        print "reponse is %s" % response.content
        self.assertEqual('responseString=%s&action=end' % urllib.quote('Your session has ended. Thank you.'), response.content)

# view tests
class UssdTestCase(TestCase):
    def setUp(self):
        self.menu_items = MenuItem.
        self.ussd_session = USSDSession.objects.create(transaction_id='1', connection='1234567', \
                                                       ussd_request_string='hello rapidsms', current)
        #self.client = Client()
        c = Client()
        #s = self.client.session
        response = c.post('ussd/')
        self.assertEqual(response.status_code, 302)
