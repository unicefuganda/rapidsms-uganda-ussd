from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.conf import settings
import urllib

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

#class ViewTest(TestCase): #pragma: no cover
#
#    def setUp(self):


