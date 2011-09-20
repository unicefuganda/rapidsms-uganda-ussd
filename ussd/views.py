from .forms import YoForm
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext

def ussd(req, input_form=YoForm, request_method='GET', output_template='ussd/yo.txt'):
    if request_method == 'GET' and req.GET:
        form = input_form(req.GET)
    elif request_method == 'POST' and req.POST:
        form = input_form(req.POST)
    else:
        return HttpResponse(status=404)
    if form.is_valid():
        pass

    return render_to_response(output_template, {
        'response_content':'Hello%2C+World%21',
        'action':'end',
    }, context_instance=RequestContext(req))
