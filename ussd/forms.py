from .models import USSDSession, MenuItem
from django import forms
from rapidsms.models import Connection
from uganda_common.utils import assign_backend
import datetime

class YoForm(forms.Form):
    # This is a unique session identifier which will be maintained for the 
    # entire USSD session.
    transactionId = forms.CharField()
    # The time the USSD request came in, in the following format:
    # YYYYMMDD(T)HH:MM:SS
    transactionTime = forms.CharField()
    # The telephone number of the subscriber who is interacting with the USSD
    # code.
    msisdn = forms.CharField()
    #This is the number the subscriber dialed. For example, if the subscriber dialed *150#, 
    # 150 is the service code, the max length is 4
    ussdServiceCode = forms.CharField()
    # This is information which was input by the subscriber.
    ussdRequestString = forms.CharField(required=False)
    # This indicates whether the incoming request is a response to a previously open request. 
    # Takes two possible string values namely "true" or "false".
    response = forms.CharField(required=False)

    def clean_msisdn(self):
        cleaned_data = self.cleaned_data
        identity, backend = assign_backend(cleaned_data['msisdn'])
        c, created = Connection.objects.get_or_create(identity=identity, backend=backend)
        return c

    def clean_transactionTime(self):
        cleaned_data = self.cleaned_data
        transaction_time = cleaned_data['transactionTime']
        try:
            cleaned_data['transactionTime'] = datetime.datetime.strptime(transaction_time, \
                                                                              '%Y%m%dT%H:%M:%S')
        except ValueError:
            raise forms.ValidationError("Invalid transaction time: %s" % transaction_time)
        return cleaned_data['transactionTime']

    def clean(self):
        cleaned_data = self.cleaned_data
        transaction_id = cleaned_data.get('transactionId')

        try:
            session = USSDSession.objects.get(transaction_id=transaction_id)
            cleaned_data['transactionId'] = session
        except USSDSession.DoesNotExist:
            try:
                root_item = MenuItem.tree.root_nodes()[0]
                session = USSDSession.objects.create(transaction_id=transaction_id, \
                                                     connection=cleaned_data.get('msisdn'), \
                                                     current_menu_item=root_item)
                cleaned_data['transactionId'] = session
            except IndexError:
                raise forms.ValidationError("No Root Menu Items exist!")

        return cleaned_data
