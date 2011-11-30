from django.db import models
from django.forms import ValidationError
from mptt.models import MPTTModel
from rapidsms.models import Contact, Connection
from uganda_common.models import PolymorphicManager, PolymorphicMixin

from rapidsms_xforms.models import XForm, XFormSubmission, XFormSubmissionValue, XFormField, xform_received
import django
import mptt
from django.conf import settings

# fired right before each screen gets a chance to process its input
ussd_pre_transition = django.dispatch.Signal(providing_args=["screen", "input", "session"])
ussd_complete = django.dispatch.Signal(providing_args=["session"])

class BackNavigation(Exception):
    """
    Can be thrown by screens based on particular input, or by 
    signal handlers, causing a back navigation.  This will pop the navigation stack and
    allow users to move to the previous navigation without storing any
    additional records in the session.
    """
    pass

class TransitionException(Exception):
    """
    Fired by pre_transition signal handlers to interrupt the normal
    flow of the USSD session.  These handlers will specify the screen
    that the session should jump to by raising this exception, with
    the appropriate screen set.
    """
    def __init__(self, screen, **kwargs):
        Exception.__init__(self, **kwargs)
        self.screen = screen

class Screen(MPTTModel, PolymorphicMixin):
    """
    This is the parent class for all Screen Types.  Subclasses must implement, at
    a minimum, the following:
    * __unicode()__ : This is what is displayed to the user's mobile when they navigate
     to this screen
    * accept_input : After this screen is displayed to their user, this screen gets a chance
    to react based on the input, using the functionality in this method.
    Optionally, the subclass can override
    get_label() and is_terminal() to add custom behavior
    """
    # Because subclasses override *methods*, but will normally be retrieved by the
    # Screen superclass, we need a way to dynamically downcast to the most specific
    # class type to invoke __unicode__, accept_input, etc.
    objects = PolymorphicManager()

    def __unicode__(self):
        raise NotImplementedError('Subclasses must override this method')

    def accept_input(self, input, session=None):
        raise NotImplementedError('Subclasses must override this method')

    def is_terminal(self):
        return True

    slug = models.SlugField(primary_key=True)

    # The label to display when navigating to this submenu
    label = models.CharField(max_length=50)

    # The order this item should be displayed from it's parent menu, if 
    # the parent *is-a* menu
    # (ignored for non-menu classes)
    order = models.IntegerField(default=0)

    # This is the previous Screen in terms of navigation (for tree-based, menued navigation)
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    def get_label(self):
        """
        In the case of menus, it is the label of the children that are displayed
        as menu options.
        """
        return self.label


class Menu(Screen, PolymorphicMixin):
    """
    Menus are basic navigational screens, allow the user to move from this screen
    to one of the menu's children by selecting a number, or '#' to move backwards
    to the previous menu (if one exists).
    """
    objects = PolymorphicManager()

    has_errors = False
    error_text = ''

    def __unicode__(self):
        """
        This renders a standard menu, based on the children of the 
        current menu item.  An example might be:

        1. Apples
        2. Fruit
        3. MEAT
        #. Back
        """
        toret = []
        for label, order in self.get_submenu_labels():
            toret.append((order, label,))

        if self.parent:
            toret.append(('#', 'Back'))
        toret = "\n".join("%s. %s" % (order, label) for order, label in toret)

        if self.has_errors:
            toret = "%s\n%s" % (self.error_label, toret)

        return toret

    def get_submenu_labels(self):
        '''
        returns the labels of the children of the current MenuItem, as an iterable,
        for rendering to a display
        
        example return value:
        [('meat',1),('vegetables',2),('fruits', 4)]
        '''
        for c in self.get_children().order_by('order'):
            yield c.get_label(), c.order

    def is_terminal(self):
        return self.get_children().count() == 0

    def accept_input(self, input, session=None):
        try:
            order = int(input)
            return self.get_children().get(order=order)
        except ValueError:
            if input == '#':
                raise BackNavigation()
            # else fall through to error case
        except Screen.DoesNotExist:
            pass

        self.has_errors = True
        self.error_label = "Invalid Menu Option."
        return self


class Question(Screen, PolymorphicMixin):
    """
    Question is a generic class for gathering questions that aren't necessarily
    tied to actual data to be gathered.  Should be subclassed for custom branching
    logic (see Field).
    """
    objects = PolymorphicManager()

    has_errors = False
    error_text = ''

    question_text = models.TextField()

    # Questions aren't menus, so there's only one default screen
    # to advance to after asking the question. 
    next = models.ForeignKey(Screen, null=True, related_name='previous')

    def get_question(self):
        return self.question_text

    def is_terminal(self):
        return self.next is None

    def accept_input(self, input, session=None):
        """
        Simply advance to the next screen. Subclasses will likely override
        this default behavior.
        """
        return self.next

    def __unicode__(self):
        if self.has_errors:
            return "%s\n%s" % (self.error_text, self.get_question())

        return self.get_question()


class Field(Question, PolymorphicMixin):
    """
    Fields are questions whose answers map to an XFormField.  As this is an
    integral part of what our USSD sessions are about, the XFormSubmissions that
    are created from these fields are stored on the USSD session object itself.
    """
    objects = PolymorphicManager()

    # The field this question is associated with
    field = models.ForeignKey(XFormField)

    def get_question(self):
        # Can use the built-in xformfield question, or a custom question
        return self.field.question or Question.get_question(self)

    def accept_input(self, input, session=None):
        try:
            field = self.field
            val = field.clean_submission(input, 'ussd')

            # try to get an existing submission
            try:
                submission = session.submissions.get(xform=self.field.xform)
            except XFormSubmission.DoesNotExist:
                submission = XFormSubmission.objects.create(xform=self.field.xform, has_errors=True)
                session.submissions.add(submission)

            try:
                # try deleting any previous values for this amount
                subval = submission.values.get(attribute=self.field, entity_id=submission.pk)
                subval.delete()
            except XFormSubmissionValue.DoesNotExist:
                pass

            submission.values.create(attribute=self.field, value=val, entity=submission)
            return self.next
        except ValidationError, e:
            self.error_text = "\n".join(e.messages)
            self.has_errors = True
            return self


class StubScreen(Screen, PolymorphicMixin):

    objects = PolymorphicManager()
    """
    This is a stub for passing to the view, used in special cases 
    (backwards navigation, unexpected ending) that isn't
    stored in the session.
    """
    terminal = models.BooleanField(default=True)
    text = models.TextField(default='Your session has ended, thank you.', null=False)

    def __unicode__(self):
        return self.text

    def is_terminal(self):
        return self.terminal


class Session(models.Model):

    #a unique session identifier which is maintained for an entire USSD session/transaction
    transaction_id = models.CharField(max_length=100)

    #The telephone number of the subscriber interacting with the USSD code
    # match this with 'msisdn'
    connection = models.ForeignKey(Connection)

    submissions = models.ManyToManyField(XFormSubmission)

    def get_initial_screen(self):
        try:
            toret = getattr(settings, 'INITIAL_USSD_SCREEN', Screen.tree.root_nodes()[0])
            if callable(toret):
                toret = toret()
            return Screen.objects.get(slug=toret)
        except IndexError:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured('You need to supply an INITIAL_USSD_SCREEN variable in your settings.py')
        except Screen.DoesNotExist:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured("You need to supply a proper INITIAL_USSD_SCREEN variable in your settings.py, not Screen with slug '%s' was found" % toret)

    def last_screen(self):
        try:
            return self.navigations.latest('date').screen
        except Navigation.DoesNotExist:
            return None

    def back(self):
        '''
        Return to the previous menu in navigation (i.e., the second-to-last screen
        in navigations).
        '''
        navs = self.navigations.order_by('-date')
        if navs.count():
            navs[0].delete()

        # don't return the screens unicode method, as this may not
        # have the full text we're looking for (screens can supply
        # state-driven text that we will have lost at this point).
        try:
            return self.navigations.all().latest('date').text
        except Navigation.DoesNotExist:
            return StubScreen().text


    def advance_progress(self, input):
        '''
        Navigate down the tree, based on the number the user has input.
        '''
        screen = self.last_screen()
        if not screen:
            screen = self.get_initial_screen()
            self.navigations.create(session=self, screen=screen, text=str(screen.downcast()))
            return screen.downcast()

        nav = self.navigations.latest('date')
        nav.response = input
        nav.save()

        try:
            ussd_pre_transition.send(sender=self, screen=screen, input=input, session=self)
            next = screen.downcast().accept_input(input, self)
            if not next:
                # this is actually an improperly configured USSD menu, but
                # we're relaxing constraints and not blowing up in the
                # case of a leaf node without any successor screen
                next = StubScreen()
            self.navigations.create(session=self, screen=next, text=str(next.downcast()))
            if next.downcast().is_terminal():
                self.complete()
            return next.downcast()
        except BackNavigation:
            return StubScreen(text=self.back(), terminal=False)
        except TransitionException as e:
            next = e.screen
            self.navigations.create(session=self, screen=next, text=str(next.downcast()))
            if next.downcast().is_terminal():
                self.complete()
            return next.downcast()

    def complete(self):
        self.submissions.update(has_errors=False)
        ussd_complete.send(sender=self, session=self)


class Navigation(models.Model):
    """
    A Navigation is a record of a single screen that the user viewed, and together
    these comprise a stack of navigations the user has made within a session.  Because
    the text rendered to screen may be state-driven (i.e., based on erroneous input, etc.)
    The actual text sent is stored, along with the Screen that generated it.  In this way,
    when a user navigates backwards, they'll receive the previous text sent, not the stateless
    screen text from an initial navigation.
    """
    screen = models.ForeignKey(Screen)
    text = models.TextField()
    response = models.TextField()
    date = models.DateTimeField(auto_now_add=True)
    session = models.ForeignKey(Session, related_name='navigations')


