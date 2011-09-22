from .forms import YoForm
from .models import MenuItem
from django.forms import ValidationError
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from rapidsms_xforms.models import XFormSubmission
import urllib

def ussd(req, input_form=YoForm, request_method='GET', output_template='ussd/yo.txt'):
    form = None
    if request_method == 'GET' and req.GET:
        form = input_form(req.GET)
    elif request_method == 'POST' and req.POST:
        form = input_form(req.POST)
    if form and form.is_valid():
        session = form.cleaned_data['transactionId']
        request_string = form.cleaned_data['ussdRequestString']
        response_content = ''
        if session.current_menu_item:
            if request_string:
                try:
                    order = int(request_string)
                    session.advance_menu_progress(order)
                except ValueError:
                    order = -1
                    response_content += "Invalid Menu Option.\n"

            if session.error_case():
                response_content = 'Your session has ended. Thank you.'
                action = 'end'
            else:
                response_content += session.get_menu_text()
                action = 'request'

        elif session.current_xform:
            response_content, action = session.process_xform_response(request_string)


        return render_to_response(output_template, {
            'response_content':urllib.quote(response_content),
            'action':action,
        }, context_instance=RequestContext(req))

    return HttpResponse(status=404)

