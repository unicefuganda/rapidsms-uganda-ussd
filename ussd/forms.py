from .models import USSDSession
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
    ussdRequestString = forms.CharField()
    # This indicates whether the incoming request is a response to a previously open request. 
    # Takes two possible string values namely "true" or "false".
    response = forms.CharField()

    def clean_msisdn(self):
        identity, backend = assign_backend(self.cleaned_data['msisdn'])
        c, created = Connection.objects.get_or_create(identity=identity, backend=backend)
        self.cleaned_data['msisdn'] = c
        return self.cleaned_data

    def clean_transactionTime(self):
        transaction_time = self.cleaned_data['transactionTime']
        try:
            self.cleaned_data['transactionTime'] = datetime.datetime.strptime(transaction_time, \
                                                                              '%Y%m%d(T)%H:%M:%S')
        except ValueError:
            raise forms.ValidationError("Invalid transaction time: %s" % transaction_time)
        return self.cleaned_data

    def clean(self):
        cleaned_data = self.cleaned_data
        transaction_id = cleaned_data.get('transactionId')
        try:
            session = USSDSession.objects.get(transaction_id=transaction_id)
            self.cleaned_data['transactionId'] = session
        except USSDSession.DoesNotExist:
            session = USSDSession.objects.create(transaction_id=transaction_id, connection=self.cleaned_data.get('msisdn'))
            self.cleaned_data['transactionId'] = session

        return cleaned_data

