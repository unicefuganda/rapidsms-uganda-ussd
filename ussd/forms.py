from django import forms
from rapidsms.models import Connection
from uganda_common.utils import assign_backend

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

    def clean(self):
        cleaned_data = self.cleaned_data
        transaction_id = cleaned_data.get('transactionId')
        try:
            # Get Transaction model with this unique ID
            pass
        except: # TransactionModel.DoesNotExist
            # Create a new Transaction for this Connection
            pass

        return cleaned_data
