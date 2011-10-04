from django.db import models
from django.forms import ValidationError
from mptt.models import MPTTModel
from rapidsms.models import Contact, Connection

from rapidsms_xforms.models import XForm, XFormSubmission, xform_received
import mptt


class MenuItem(MPTTModel):
    # This is the previous Menu Item in terms of navigation
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')

    # The label to display when navigating to this submenu
    label = models.CharField(max_length=50)

    # an XForm, for "leaf" menu items that drop the user straight into a question-and-answer
    # session for collecting a form
    xform = models.ForeignKey(XForm, null=True, blank=True)

    # The order this menu item should be displayed from it's parent menu
    order = models.IntegerField()

    # The step in the xform (corresponding to the field order),
    # before which the user should be prompted if they want to continue entering data 
    skip_option = models.IntegerField(default= -1)

    # Use a context-specific question to ask the user if they wish to enter further optional
    # fields.  An affirmative answer should mean continue, i.e.
    # "do you have more diseases to report?"
    skip_question = models.TextField(null=True, blank=True)

    def get_submenu_labels(self):
        '''
        returns the labels of the children of the current MenuItem, in order,
        for rendering to a display
        
        example return value:
        ['meat','vegetables','fruits']
        '''
        return self.get_children().order_by('order').values_list('label', flat=True)

    def get_nth_item(self, num):
        '''
        return the order number of a child menu item, based on its actual order relative to 
        this node.
        For example, if the children of this MenuItem have orders of 2, 4 and 6,
        get_nth_item(2) would return 4 the `order` of the *second* child MenuItem.
        
        If this menu doesnt have n children, a ValueError is thrown.
        '''
        try:
            return self.get_children().order_by('order')[num - 1].order
        except IndexError:
            raise ValueError("menu out of valid range")

    def __unicode__(self):
        return "%d: %s" % (self.order, self.label)


class USSDSession(models.Model):
    """Model to hold session information"""

    #a unique session identifier which is maintained for an entire USSD session/transaction
    transaction_id = models.CharField(max_length=100)

    #The telephone number of the subscriber interacting with the USSD code
    # match this with 'msisdn'
    connection = models.ForeignKey(Connection)

    #The information that the subscriber inputs to the system.
    ussd_request_string = models.CharField(max_length=100)

    # The current menu item, i.e. its *children* will be rendered
    # during the next dialogue
    current_menu_item = models.ForeignKey('MenuItem', null=True)

    # The current xform, if the user has now navigated to an
    # xform and is actively answering questions attributed to a report
    current_xform = models.ForeignKey(XForm, null=True)

    # The submission the user is building as a result of this USSD session
    submission = models.ForeignKey(XFormSubmission, null=True)

    # Is the current screen a prompt to skip the remaining fields in an xform
    is_skip_prompt = models.BooleanField(default=False)

    #the step that the user has reached during questioning e.g. during a poll
    xform_step = models.IntegerField(null=True)

    def error_case(self):
        '''
        This is the equivalent of an ImproperlyConfiguredException...
        i.e., this particular MenuItem tree is not correctly navigable, and has
        potential situations where the user has nothing further to do.  In this
        case, fail gracefully (or not-so-gracefully) by telling the user their 
        session has ended.  Returns True if the session is in an error state and 
        must be ended, False if everything's okay
        '''
        return not (self.current_menu_item or self.current_xform) or \
            (self.current_menu_item and self.current_menu_item.get_children().count() == 0 and \
             not self.current_xform)

    def back(self):
        '''
        Return to the previous menu in navigation (i.e., the parent MenuItem of the
        current one).
        '''
        if not self.current_menu_item or not self.current_menu_item.parent:
            raise ValueError("Can't move back from this menu!")
        previous_menu_item = self.current_menu_item.parent
        self.current_menu_item = previous_menu_item
        self.save()

    def advance_menu_progress(self, order):
        '''
        Navigate down the tree, based on the number the user has input.
        '''
        try:
            order = int(order)
            self.current_menu_item = self.current_menu_item.get_children().get(order=order)
            if self.current_menu_item.get_children().count() == 0 and self.current_menu_item.xform:
                self.current_xform = self.current_menu_item.xform
                self.xform_step = self.current_xform.fields.order_by('order')[0].order
                self.submission = XFormSubmission.objects.create(xform=self.current_xform, \
                                                                    has_errors=True)
            self.save()
        except ValueError:
            raise ValueError("Invalid character")
        except MenuItem.DoesNotExist:
            raise ValueError("Invalid Menu Option. %r" % order)

    def process_xform_response(self, request_string):
        '''
        This method processes the current request_string, based on the progress along
        this particular XForm (based on current_xform and xform_step).  If, after processing
        this step, the session has reached the skip_option question, the session will update
        is_skip_prompt to True (TODO).  After processing the current field (and raising any ValidationErrors
        that may occur), this method attempts to advance to the next XFormField in the XForm.

        (TODO) Returns True if there are more fields to gather, False if the XFormSubmission is complete.
        '''

        try:
            field = self.current_xform.fields.get(order=self.xform_step)
            val = field.clean_submission(request_string, 'ussd')
            self.submission.values.create(attribute=field, value=val, entity=self.submission)
            self.xform_step = self.current_xform.fields.filter(order__gt=self.xform_step).order_by('order')[0].order
            self.is_skip_prompt = (self.current_menu_item.skip_option == self.xform_step)

            # if submission isn't complete, return True ('True' => collect more data)
            self.save()
            return True
        except IndexError:
            self.submission.has_errors = False
            self.submission.response = self.current_xform.response
            xform_received.send(sender=self.current_xform, xform=self.current_xform, submission=self.submission)
            self.submission.save()
            return False

