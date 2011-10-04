from django.test import TestCase
from django.test.client import Client
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from rapidsms_xforms.models import XForm, XFormField, XFormSubmission
from ussd.models import MenuItem
from ussd.views import ussd, __render_menu__
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
            'transactionTime':'20110101T01:01:01',
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
        response = ussd(self.factory.post(self.url, {\
            'transactionId':transaction_id, \
            'transactionTime':datetime.datetime.now().strftime('%Y%m%dT%H:%M:%S'),
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
        self.back = '#'

    def testDepth(self):
        self.assertSessionNavigation('foo', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('foo', '2', __render_menu__(self.getMenuItem([2])))
        self.assertSessionNavigation('foo', '#', __render_menu__(self.root_menu))
        self.assertSessionNavigation('foo', '2', __render_menu__(self.getMenuItem([2])))
        self.assertSessionNavigation('foo', '1', __render_menu__(self.getMenuItem([2, 1])))

        self.assertSessionNavigation('foo', '1', 'Your session has ended. Thank you.', action='end')


    def testBreadth(self):
        self.assertSessionNavigation('bar', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('bar', '3', __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('bar', '2', __render_menu__(self.getMenuItem([3, 2])))
        self.assertSessionNavigation('bar', '2', 'Your session has ended. Thank you.', action='end')

    def testBackwardsForwards(self):
        hash = self.back
        self.assertSessionNavigation('foo', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('foo', '2', __render_menu__(self.getMenuItem([2])))
        self.assertSessionNavigation('foo', '1', __render_menu__(self.getMenuItem([2, 1])))
        self.assertSessionNavigation('foo', hash, __render_menu__(self.getMenuItem([2])))
        self.assertSessionNavigation('foo', hash, __render_menu__(self.root_menu))

        self.assertSessionNavigation('foo', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('foo', '3', __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('foo', '2', __render_menu__(self.getMenuItem([3, 2])))
        self.assertSessionNavigation('foo', hash, __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('foo', hash, __render_menu__(self.root_menu))
        # Don't allow backwards navigation from the root
        self.assertSessionNavigation('foo', hash, "Invalid Menu Option.\n%s" % __render_menu__(self.root_menu))

    def testBadMenuSelect(self):
        self.assertSessionNavigation('whoa', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('whoa', '27', "Invalid Menu Option.\n%s" % __render_menu__(self.root_menu))
        self.assertSessionNavigation('whoa', 'apples', "Invalid Menu Option.\n%s" % __render_menu__(self.root_menu))

    def testXFormSubmission(self):
        xform = XForm.objects.create(keyword='test', name='test xform', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        xform.fields.create(xform=xform, name='t1', field_type=XFormField.TYPE_INT, command='test_t1', question='How old are you?', order=0)
        xform.fields.create(xform=xform, name='t2', field_type=XFormField.TYPE_INT, command='test_t2', question='How many tests have you run?', order=1)
        mi = self.getMenuItem([3, 2, 2])
        mi.xform = xform
        mi.save()

        self.assertSessionNavigation('bar', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('bar', '3', __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('bar', '2', __render_menu__(self.getMenuItem([3, 2])))
        self.assertSessionNavigation('bar', '2', 'How old are you?')
        self.assertSessionNavigation('bar', '27', 'How many tests have you run?')
        self.assertSessionNavigation('bar', '270', 'thanks for testing', action='end')

        self.assertEquals(XFormSubmission.objects.count(), 1)
        submission = XFormSubmission.objects.all()[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 27)
        self.assertEquals(submission.values.get(attribute__slug='test_test_t2').value_int, 270)
        self.failIf(submission.has_errors)

    def testXFormSkip(self):
        xform = XForm.objects.create(keyword='test', name='test xform', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        xform.fields.create(xform=xform, name='t1', field_type=XFormField.TYPE_INT, command='test_t1', question='How old are you?', order=0)
        xform.fields.create(xform=xform, name='t2', field_type=XFormField.TYPE_INT, command='test_t2', question='How many tests have you run?', order=1)
        mi = self.getMenuItem([3, 2, 2])
        mi.xform = xform
        mi.skip_option = 1
        mi.skip_question = "Do you want to keep testing?"
        mi.save()

        self.assertSessionNavigation('bar', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('bar', '3', __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('bar', '2', __render_menu__(self.getMenuItem([3, 2])))
        self.assertSessionNavigation('bar', '2', 'How old are you?')
        self.assertSessionNavigation('bar', '27', 'Do you want to keep testing?\n1. Yes\n2. No')
        self.assertSessionNavigation('bar', '1', 'How many tests have you run?')
        self.assertSessionNavigation('bar', '270', 'thanks for testing', action='end')

        self.assertEquals(XFormSubmission.objects.count(), 1)
        submission = XFormSubmission.objects.all()[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 27)
        self.assertEquals(submission.values.get(attribute__slug='test_test_t2').value_int, 270)
        self.failIf(submission.has_errors)

        self.assertSessionNavigation('foo', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('foo', '3', __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('foo', '2', __render_menu__(self.getMenuItem([3, 2])))
        self.assertSessionNavigation('foo', '2', 'How old are you?')
        self.assertSessionNavigation('foo', '28', 'Do you want to keep testing?\n1. Yes\n2. No')
        self.assertSessionNavigation('foo', '2', 'thanks for testing', action='end')

        self.assertEquals(XFormSubmission.objects.count(), 2)
        submission = XFormSubmission.objects.exclude(pk=submission.pk)[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 28)
        self.failIf(submission.has_errors)



    def testBadXFormSubmission(self):
        xform = XForm.objects.create(keyword='test', name='test xform', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        xform.fields.create(xform=xform, name='t1', field_type=XFormField.TYPE_INT, command='test_t1', question='How old are you?', order=0)
        xform.fields.create(xform=xform, name='t2', field_type=XFormField.TYPE_INT, command='test_t2', question='How many tests have you run?', order=1)
        mi = self.getMenuItem([3, 2, 2])
        mi.xform = xform
        mi.save()

        self.assertSessionNavigation('whoa', '', __render_menu__(self.root_menu))
        self.assertSessionNavigation('whoa', '27', "Invalid Menu Option.\n%s" % __render_menu__(self.root_menu))
        self.assertSessionNavigation('whoa', '3', __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('whoa', 'apples', "Invalid Menu Option.\n%s" % __render_menu__(self.getMenuItem([3])))
        self.assertSessionNavigation('whoa', '2', __render_menu__(self.getMenuItem([3, 2])))
        self.assertSessionNavigation('whoa', '2', 'How old are you?')
        # bad user says he is "strawberry" years old
        self.assertSessionNavigation('whoa', 'strawberry', '+test_t1 parameter must be an even number.How old are you?')

        self.assertSessionNavigation('whoa', '20', 'How many tests have you run?')
        # bad user types an invalid value "what?", he probably thought this is conversational.
        self.assertSessionNavigation('whoa', 'what?', '+test_t2 parameter must be an even number.How many tests have you run?')
        self.assertSessionNavigation('whoa', '270', 'thanks for testing', action='end')

        self.assertEquals(XFormSubmission.objects.count(), 1)
        submission = XFormSubmission.objects.all()[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 20)
        self.assertEquals(submission.values.get(attribute__slug='test_test_t2').value_int, 270)
        self.failIf(submission.has_errors)
