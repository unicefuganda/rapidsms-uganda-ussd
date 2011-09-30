from django.db import models
from django.forms import ValidationError
from mptt.models import MPTTModel
from rapidsms.models import Contact, Connection

from rapidsms_xforms.models import XForm, XFormSubmission, xform_received
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
        if self.error_case():
            raise ValueError("Invalid Action!")
        if self.current_menu_item:
            return self.current_menu_item.get_menu_text()
        elif self.current_xform:
            return self.current_xform.fields.get(order=self.xform_step).question

    def advance_menu_progress(self, order):
        try:
            next_menu_item = self.current_menu_item.get_children().get(order=order)
            if next_menu_item.get_children().count() == 0 and next_menu_item.xform:
                self.current_menu_item = None
                self.current_xform = next_menu_item.xform
                self.xform_step = self.current_xform.fields.order_by('order')[0].order
                self.submission = XFormSubmission.objects.create(xform=self.current_xform, \
                                                                    has_errors=True)
            else:
                self.current_menu_item = next_menu_item
            self.save()
        except MenuItem.DoesNotExist:
            raise ValueError("Invalid menu option %d" % order)
    # work needed on function

    def back(self,order):
        try:
            # if current menu item has ancestors
            previous_menu_item = self.current_menu_item.get_ancestors(ascending=True).get(order=order)
            if previous_menu_item.get_ancestors(ascending=True).count() == 0 and previous_menu_item.xform:
                self.previous_menu_item = None
                self.current_xform = previous_menu_item.xform
                self.xform_step = self.current_xform.fields.order_by('order')[0].order
                self.submission = XFormSubmission.objects.create(xform=self.current_xform,has_errors=True)

            else:
                self.current_xform = previous_menu_item
            self.save()
        except MenuItem.DoesNotExist:
            raise ValueError("Invalid menu option %d"%order)


    def process_xform_response(self, request_string):
        response_content = ''
        try:
            if request_string and self.current_xform.fields.filter(order=self.xform_step).count():
                try:
                    field = self.current_xform.fields.get(order=self.xform_step)
                    val = field.clean_submission(request_string, 'ussd')
                    self.submission.values.create(attribute=field, value=val, entity=self.submission)
                    self.xform_step = self.current_xform.fields.filter(order__gt=self.xform_step).order_by('order')[0].order
                    self.save()
                except ValidationError, e:
                    response_content += "\n".join(e.messages)
                except IndexError:
                    self.submission.has_errors = False
                    self.submission.response = self.current_xform.response
                    xform_received.send(sender=self.current_xform, xform=self.current_xform, submission=self.submission)
                    self.submission.save()
                    return self.submission.response, 'end'

            response_content += self.current_xform.fields.get(order=self.xform_step).question
            action = 'request'
        except IndexError:
            response_content = 'Your session has ended. Thank you.'
            action = 'end'
        return response_content, action
