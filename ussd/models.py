from django.db import models
from django.forms import ValidationError
from mptt.models import MPTTModel
from rapidsms.models import Contact, Connection

from rapidsms_xforms.models import XForm, XFormSubmission
import mptt


class MenuItem(MPTTModel):
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    label = models.CharField(max_length=50)
    xform = models.ForeignKey(XForm, null=True)
    order = models.IntegerField()

    def get_menu_text(self):
        return "\n".join(["%d: %s" % (i.order, i.label) for i in self.get_children().order_by('order')])

class USSDSession(models.Model):
    """Model to hold session information"""

    #a unique session identifier which is maintained for an entire USSD session/transaction
    transaction_id = models.CharField(max_length=100)

    #The telephone number of the subscriber interacting with the USSD code
    # match this with 'msisdn'
    connection = models.ForeignKey(Connection)

    #The information that the subscriber inputs to the system.
    ussd_request_string = models.CharField(max_length=100)

    current_menu_item = models.ForeignKey('MenuItem', null=True)
    current_xform = models.ForeignKey(XForm, null=True)
    submission = models.ForeignKey(XFormSubmission, null=True)

    #create XForm models and preferably fk to that.
    xform_step = models.IntegerField(null=True)

    def error_case(self):
        return not (self.current_menu_item or self.current_xform) or \
            (self.current_menu_item and self.current_menu_item.get_children().count() == 0)

    def get_menu_text(self):
        return self.current_menu_item.get_menu_text()

    def advance_menu_progress(self, order):
        try:
            next_menu_item = self.current_menu_item.get_children().get(order=order)
            if next_menu_item.get_children().count() == 0 and next_menu_item.xform:
                self.current_menu_item = None
                self.current_xform = next_menu_item.xform
            else:
                self.current_menu_item = next_menu_item
            self.save()
        except MenuItem.DoesNotExist:
            pass

    def process_xform_response(self, request_string):
        response_content = ''
        try:
            if request_string and self.current_xform.fields.filter(order=self.xform_step).count():
                try:
                    field = self.current_xform.fields.get(order=self.xform_step)
                    val = field.clean_submission(request_string)
                    self.submission.values.create(attribute=field, value=val, entity=self.submission)
                    self.xform_step = self.current_xform.fields.filter(order__gt=self.xform_step).order_by('order')[0].order
                    self.save()
                except ValidationError, e:
                    response_content += "\n".join(e.messages)

            else:
                # create new submission object
                self.xform_step = self.current_xform.fields.order_by('order')[0].order
                self.submission = XFormSubmission.objects.create(xform=self.current_xform, \
                                                                    has_errors=True)
            response_content += self.current_xform.fields.get(order=self.xform_step).question
            action = 'request'
        except IndexError:
            response_content = 'Your session has ended. Thank you.'
            action = 'end'
        return response_content, action
