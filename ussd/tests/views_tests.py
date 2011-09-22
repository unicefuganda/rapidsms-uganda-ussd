from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse
from rapidsms.models import Connection
from ussd.models import MenuItem
import urllib

class BasicTest(TestCase):

    def testNoExplosions(self):
        client = Client()
        # No menu in the DB, this should still return something
        url = reverse('ussd.views.ussd')
        print "url is %s" % url
        response = client.get(reverse('ussd.views.ussd'), {\
            'transactionId':'foo', \
            'transactionTime':'20110101(T)01:01:01',
            'msisdn':'8675309',
            'ussdServiceCode':'300',
            'ussdRequestString':'',
        })
        self.assertEquals(response.status_code, 404)

class MenuInteractionTests(TestCase):

    def __create_menu_recurse__(self, parent, menulist):
        order = 1
        for label, submenu in menulist:
            menu_item = MenuItem.objects.create(order=order, label=label, parent=parent, xform=None)
            self.__create_menu_recurse__(menu_item, submenu)
            order += 1

    def __create_menu__(self, menulist):
        self.root_menu = MenuItem.objects.create(order=0, label='root', parent=None, xform=None)
        self.__create_menu_recurse__(self.root_menu, menulist)
        self.root_menu = MenuItem.objects.get(pk=self.root_menu.pk)

    def setUp(self):
        self.client = Client()
        self.url = reverse('ussd.views.ussd')
        self.__create_menu__(\
            [('Fruits', []),
             ('Vegetables', [('Pointless Rabit Food', [('Carrots', [])])]),
             ('MEAT', [
                 ('Bacon', []),
                 ('Chicken', [('Spicy', []), ('Fried', []), ('Cajun', [])]),
                 ('Turducken', [])
             ])]
        )

    def testDepth(self):
        menu_items = MenuItem.objects.all()
        response = self.client.get(self.url, {\
            'transactionId':'foo', \
            'transactionTime':'20110101(T)01:01:01',
            'msisdn':'8675309',
            'ussdServiceCode':'300',
            'ussdRequestString':'',
        })
        self.assertEquals(response.content, 'responseString=%s&action=request' % urllib.quote(self.root_menu.get_menu_text()))
        response = self.client.get(self.url, {\
            'transactionId':'foo', \
            'transactionTime':'20110101(T)01:01:01',
            'msisdn':'8675309',
            'ussdServiceCode':'300',
            'ussdRequestString':'1',
        })
        self.assertEquals(response.content, 'responseString=%s&action=request' % urllib.quote(self.root_menu.get_children().get(order=1).get_menu_text()))
