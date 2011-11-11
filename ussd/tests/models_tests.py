from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from django.conf import settings
import urllib
from rapidsms_xforms.models import XForm
from rapidsms.models import Connection, Backend, Contact


class UssdTestCase(TestCase):
    def setUp(self):
        pass

    def testContacts(self):
        self.assertEquals(1, 1)
