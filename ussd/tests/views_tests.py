from django.test import TestCase
from django.test.client import Client
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from rapidsms.models import Connection
from ussd.models import MenuItem
from ussd.views import ussd
import datetime
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

    def assertSessionNavigation(self, transaction_id, request, expected_response, action='request'):
        response = ussd(self.factory.get(self.url, {\
            'transactionId':transaction_id, \
            'transactionTime':datetime.datetime.now().strftime('%Y%m%d(T)%H:%M:%S'),
            'msisdn':'8675309',
            'ussdServiceCode':'300',
            'ussdRequestString':request,
        }))
        self.assertEquals(response.content, 'responseString=%s&action=%s' % (urllib.quote(expected_response), action))

    def getMenuItem(self, order_list):
        to_ret = self.root_menu
        for num in order_list:
            to_ret = to_ret.get_children().get(order=num)
        return to_ret

    def setUp(self):
        self.factory = RequestFactory()
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
        self.assertSessionNavigation('foo', '', self.root_menu.get_menu_text())
        self.assertSessionNavigation('foo', '2', self.getMenuItem([2]).get_menu_text())
        self.assertSessionNavigation('foo', '1', self.getMenuItem([2, 1]).get_menu_text())
        self.assertSessionNavigation('foo', '1', 'Your session has ended. Thank you.', action='end')

    def testBreadth(self):
        self.assertSessionNavigation('bar', '', self.root_menu.get_menu_text())
        self.assertSessionNavigation('bar', '3', self.getMenuItem([3]).get_menu_text())
        self.assertSessionNavigation('bar', '2', self.getMenuItem([3, 2]).get_menu_text())
        self.assertSessionNavigation('bar', '2', 'Your session has ended. Thank you.', action='end')
