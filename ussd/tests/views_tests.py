from django.test import TestCase
from django.test.client import Client
from django.test.client import RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.conf import settings
from django.core.management import call_command
from django.db.models import loading
from rapidsms.models import Connection, Backend
from rapidsms_xforms.models import XForm, XFormField, XFormSubmission
from rapidsms.contrib.locations.models import Location, LocationType
from ussd.models import Menu, Field, StubScreen, Screen, TransitionException, Session, Navigation
from ussd.views import ussd
import datetime
import urllib

class ViewTest_BROKEN():

    def setUp(self):
        # Lots of things blow up if there's not a single location
        t = LocationType.objects.create(name='country', slug='county')
        Location.objects.create(name='Uganda', type=t)

        root_menu = Menu.objects.create(slug='ussd_root', label="Ignored", order=1)
        self.factory = RequestFactory()
        self.url = reverse('ussd.views.ussd')
        child1 = Menu.objects.create(slug='child1', label="Apples", order=1, parent=root_menu)
        Menu.objects.create(slug='child11', label="Golden Delicious", order=1, parent=child1)
        Menu.objects.create(slug='child12', label="Granny Smith", order=2, parent=child1)

        User.objects.create_user('test', 'test@test.com', 'test')
        xform = XForm.objects.create(keyword='test', name='test xform', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        field1 = XFormField.objects.create(xform=xform, name='t1', field_type=XFormField.TYPE_INT, command='test_t1', question='How old are you?', order=0)
        field2 = XFormField.objects.create(xform=xform, name='t2', field_type=XFormField.TYPE_INT, command='test_t2', question='How many tests have you run?', order=1)
        xform2 = XForm.objects.create(keyword='test2', name='test xform2', response='thanks for testing', owner=User.objects.get(username='test'), site=Site.objects.get_current())
        field21 = XFormField.objects.create(xform=xform2, name='t1', field_type=XFormField.TYPE_INT, command='test2_t1', question='How tall are you (in)?', order=0)
        field22 = XFormField.objects.create(xform=xform2, name='t2', field_type=XFormField.TYPE_INT, command='test2_t2', question='How many tests will fail?', order=1)
        stub = StubScreen.objects.create(slug='stubby')
        fmenu2 = Field.objects.create(\
                    slug='test_t2', \
                    field=field2, \
                    question_text=field2.question, \
                    order=0, \
                    next=stub)
        fmenu1 = Field.objects.create(\
                    slug='test_t1', \
                    field=field1, \
                    question_text=field1.question, \
                    next=fmenu2, \
                    label='Oranges', \
                    order=2, \
                    parent=root_menu)
        fmenu22 = Field.objects.create(\
                    slug='test2_t2', \
                    field=field22, \
                    question_text=field22.question, \
                    order=0, \
                    next=fmenu1)
        fmenu21 = Field.objects.create(\
                    slug='test2_t1', \
                    field=field21, \
                    question_text=field21.question, \
                    next=fmenu22, \
                    label='Grapefruit', \
                    order=4, \
                    parent=root_menu)

        Menu.objects.create(slug='child3', label="Bananas", order=3, parent=root_menu)

    def assertSessionNavigation(self, transaction_id, request, expected_response, action='request'):
        response = ussd(self.factory.post(self.url, {\
            'transactionId':transaction_id, \
            'transactionTime':datetime.datetime.now().strftime('%Y%m%dT%H:%M:%S'),
            'msisdn':'8675309',
            'ussdServiceCode':'300',
            'ussdRequestString':request,
        }))
        self.assertEquals(response.content, 'responseString=%s&action=%s' % (urllib.quote(expected_response), action))

    def testMenu(self):
        self.assertSessionNavigation('foo', '', str(Menu.objects.get(slug='ussd_root')))
        self.assertSessionNavigation('foo', '1', str(Menu.objects.get(slug='child1')))

    def testBadMenuSelect(self):
        self.assertSessionNavigation('foo', '', str(Menu.objects.get(slug='ussd_root')))
        self.assertSessionNavigation('foo', '27', "Invalid Menu Option.\n%s" % str(Menu.objects.get(slug='ussd_root')))

    def testField(self):
        self.assertSessionNavigation('foo', '', str(Menu.objects.get(slug='ussd_root')))
        self.assertSessionNavigation('foo', '2', str(Field.objects.get(slug='test_t1')))
        self.assertSessionNavigation('foo', '45', str(Field.objects.get(slug='test_t2')))
        self.assertSessionNavigation('foo', '27', str(StubScreen()), action='end')

        self.assertEquals(XFormSubmission.objects.count(), 1)
        submission = XFormSubmission.objects.all()[0]
        self.assertEquals(submission.values.get(attribute__slug='test_test_t1').value_int, 45)
        self.assertEquals(submission.values.get(attribute__slug='test_test_t2').value_int, 27)

    def testBack(self):
        self.assertSessionNavigation('foo', '', str(Menu.objects.get(slug='ussd_root')))
        self.assertSessionNavigation('foo', '1', str(Menu.objects.get(slug='child1')))
        self.assertSessionNavigation('foo', '#', str(Menu.objects.get(slug='ussd_root')))

    def testMultiSubmission(self):
        self.assertSessionNavigation('foo', '', str(Menu.objects.get(slug='ussd_root')))
        self.assertSessionNavigation('foo', '4', str(Field.objects.get(slug='test2_t1')))
        self.assertSessionNavigation('foo', '45', str(Field.objects.get(slug='test2_t2')))
        self.assertSessionNavigation('foo', '27', str(Field.objects.get(slug='test_t1')))
        self.assertSessionNavigation('foo', '314', str(Field.objects.get(slug='test_t2')))
        self.assertSessionNavigation('foo', '56', str(StubScreen()), action='end')

        self.assertEquals(XFormSubmission.objects.count(), 2)
        submission1 = XFormSubmission.objects.get(xform__keyword='test')
        submission2 = XFormSubmission.objects.get(xform__keyword='test2')
        self.assertEquals(submission1.values.get(attribute__slug='test_test_t1').value_int, 314)
        self.assertEquals(submission1.values.get(attribute__slug='test_test_t2').value_int, 56)
        self.assertEquals(submission2.values.get(attribute__slug='test2_test2_t1').value_int, 45)
        self.assertEquals(submission2.values.get(attribute__slug='test2_test2_t2').value_int, 27)

    def testTransitionException(self):
        class ExceptionScreen(Screen):
            def __unicode__(self):
                return "Ready to Jump?"
            def accept_input(self, input, session):
                raise TransitionException(screen=StubScreen.objects.get(slug='stubby'))

        class ExceptionSession(Session):
            class Meta:
                proxy = True

            def last_screen(self):
                return ExceptionScreen()

            @property
            def navigations(self):
                return Navigation.objects.all()

        c = Connection.objects.create(identity='8675309', backend=Backend.objects.create(name='dummy'))
        s = ExceptionSession.objects.create(connection=c, transaction_id='foo')
        n = Navigation.objects.create(screen=StubScreen.objects.create(text='first', slug='notherstub'), session=s, text='ready to jump?')
        self.assertEquals(s.advance_progress('yes'), StubScreen.objects.get(slug='stubby'))

    def testErrorInput(self):
        self.assertSessionNavigation('foo', '', str(Menu.objects.get(slug='ussd_root')))
        self.assertSessionNavigation('foo', '2', str(Field.objects.get(slug='test_t1')))
        self.assertSessionNavigation('foo', 'pizza', str("+test_t1 parameter must be an even number.\n%s" % Field.objects.get(slug='test_t1')))
