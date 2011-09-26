from django.test import TestCase
from django.test.client import Client
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from rapidsms_xforms.models import XForm, XFormField, XFormSubmission
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
        self.user = User.objects.create_user('test', 'test@test.com', 'test')
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
    # test for smelly bad logic
    """
    def testBadBreadth(self):
        self.assertSessionNavigation('bar','',self.root_menu.get_menu_text())
        self.assertSessionNavigation('bar','1',self.getMenuItem([1]).get_menu_text())
        self.assertSessionNavigation('bar','2',self.getMenuItem([1,2]))
        self.assertSessionNavigation('bar','3',self.root_menu.get_menu_text())
    """
    # Test bad boy
    def testBadMenuSelect(self):
        self.assertSessionNavigation('whoa', '', self.root_menu.get_menu_text())
        self.assertSessionNavigation('whoa', '27', "Invalid Menu Option.\n%s" % self.root_menu.get_menu_text())
        self.assertSessionNavigation('whoa', 'apples', "Invalid Menu Option.\n%s" % self.root_menu.get_menu_text())

    def testXFormSubmission(self):
        xform = XForm.objects.create(keyword='test', name='test xform', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        xform.fields.create(xform=xform, name='t1', field_type=XFormField.TYPE_INT, command='test_t1', question='How old are you?', order=0)
        xform.fields.create(xform=xform, name='t2', field_type=XFormField.TYPE_INT, command='test_t2', question='How many tests have you run?', order=1)
        mi = self.getMenuItem([3, 2, 2])
        mi.xform = xform
        mi.save()

        self.assertSessionNavigation('bar', '', self.root_menu.get_menu_text())
        self.assertSessionNavigation('bar', '3', self.getMenuItem([3]).get_menu_text())
        self.assertSessionNavigation('bar', '2', self.getMenuItem([3, 2]).get_menu_text())
        self.assertSessionNavigation('bar', '2', 'How old are you?')
        self.assertSessionNavigation('bar', '27', 'How many tests have you run?')
        self.assertSessionNavigation('bar', '270', 'thanks for testing', action='end')

        self.assertEquals(XFormSubmission.objects.count(), 1)
        submission = XFormSubmission.objects.all()[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 27)
        self.assertEquals(submission.values.get(attribute__slug='test_test_t2').value_int, 270)
        self.failIf(submission.has_errors)
"""
    def testBadXformSubmission(self):
        xform = XForm.objects.create(keyword='test', name='test xform', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        xform.fields.create(xform=xform, name='t1', field_type=XFormField.TYPE_INT, command='test_t1', question='How old are you?', order=0)
        xform.fields.create(xform=xform, name='t2', field_type=XFormField.TYPE_INT, command='test_t2', question='How many tests have you run?', order=1)
        mi = self.getMenuItem([3, 2, 2])
        mi.xform = xform
        mi.save()

        self.assertSessionNavigation('bar', '', self.root_menu.get_menu_text())
        self.assertSessionNavigation('bar', '3', self.getMenuItem([3]).get_menu_text())
        self.assertSessionNavigation('bar', '2', self.getMenuItem([3, 2]).get_menu_text())
        self.assertSessionNavigation('bar', '2', 'How old are you?')
        # wrong submission
        self.assertSessionNavigation('bar', 'x', 'How many tests have you run?')
        # wrong submission type
        self.assertSessionNavigation('bar', 'xyz', 'thanks for testing', action='end')
        # if equal, this means we are collecting bad data
        self.assertEquals(XFormSubmission.objects.count(), 1)
        submission = XFormSubmission.objects.all()[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 27)
        self.assertEquals(submission.values.get(attribute__slug='test_test_t2').value_int, 270)
        self.failIf(submission.has_errors)

"""