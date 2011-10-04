from .forms import YoForm
from .models import MenuItem
from django.forms import ValidationError
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from rapidsms_xforms.models import XFormSubmission
import urllib

def __render_menu__(menuitem):
    """
    This renders a standard menu, based on the children of the 
    current menu item.  An example might be:
    
    1. Apples
    2. Fruit
    3. MEAT
    """
    labels = menuitem.get_submenu_labels()
    order = 1
    toret = []
    for label in labels:
        toret.append((order, label,))
        order += 1
    return "\n".join("%d: %s" % (order, label) for order, label in toret)

def __render_skip__(menuitem):
    """
    This prompts a user for if the want to continue filling in (optional)
    data for the current form.  The default screen will render to:
    
    Do you want to continue?
    1. Yes
    2. No
    """
    question = menuitem.skip_question or "Do you want to continue?"
    return "\n".join([question, '1. Yes', '2. No'])

def __render_data_input__(menuitem):
    return menuitem.current_xform.fields.get(order=menuitem.xform_step).question

def __render_screen_from_session__(ussdsession):
    """
    After the state for a current user input has been reflected in the model,
    this function will decide which sort of screen to render based on the updated
    session state
    """
    if ussdsession.error_case():
        return 'Your session has ended. Thank you.', 'end'
    elif not ussdsession.current_xform:
        # We're just doing regular navigation
        return __render_menu__(ussdsession.current_menu_item), 'request'
    elif ussdsession.current_menu_item.skip_option == ussdsession.current_menu_item.xform_step and \
        ussdsession.is_skip_prompt:
        # We're in the middle of collecting a form, and we've reached the point where
        # we prompt the user if they want to continue
        return __render_skip__(ussdsession.current_menu_item), 'request'
    else:
        # This is a regular data collection step, just ask the appropriate question
        return __render_data_input__(ussdsession.current_menu_item), 'request'

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
                    order = request_string
                    if int(order):
                        session.advance_menu_progress(order)
                    elif order == '#':
                        session.back()
                    else:
                        print "no acceptable response" #TODO replace with an exception
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

