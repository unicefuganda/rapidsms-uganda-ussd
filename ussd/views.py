from .forms import YoForm
from django.forms import ValidationError
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
import urllib


def ussd(req, input_form=YoForm, request_method='POST', output_template='ussd/yo.txt'):
    form = None
    if req.method == 'GET' and req.GET:
        form = input_form(req.GET)
    elif req.method == 'POST' and req.POST:
        form = input_form(req.POST)
    if form and form.is_valid():
        session = form.cleaned_data['transactionId']
        request_string = form.cleaned_data['ussdRequestString']

        response_screen = session.advance_progress(request_string)
        action = 'end' if response_screen.is_terminal() else 'request'
        return render_to_response(output_template, {
            'response_content':urllib.quote(str(response_screen)),
            'action':action,
        }, context_instance=RequestContext(req))

    return HttpResponse(status=404)
