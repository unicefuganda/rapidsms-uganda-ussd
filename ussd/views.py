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
    #. Back
    """
    labels = menuitem.get_submenu_labels()
    order = 1
    toret = []
    for label in labels:
        toret.append((order, label,))
        order += 1
    if menuitem.parent:
        toret.append(('#', 'Back'))
    return "\n".join("%s. %s" % (order, label) for order, label in toret)

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

def __render_data_input__(session):
    return session.current_xform.fields.get(order=session.xform_step).question

def __render_screen_from_session__(ussdsession):
    """
    After the state for a current user input has been reflected in the model,
    this function will decide which sort of screen to render based on the updated
    session state
    """
    if ussdsession.error_case():
        return ('Your session has ended. Thank you.', 'end',)
    elif not ussdsession.current_xform:
        # We're just doing regular navigation
        return (__render_menu__(ussdsession.current_menu_item), 'request',)
    elif ussdsession.current_menu_item.skip_option == ussdsession.xform_step and \
        ussdsession.is_skip_prompt:
        # We're in the middle of collecting a form, and we've reached the point where
        # we prompt the user if they want to continue
        return (__render_skip__(ussdsession.current_menu_item), 'request',)
    else:
        # This is a regular data collection step, just ask the appropriate question
        return (__render_data_input__(ussdsession), 'request',)

def ussd(req, input_form=YoForm, request_method='POST', output_template='ussd/yo.txt'):
    form = None
    if request_method == 'GET' and req.GET:
        form = input_form(req.GET)
    elif request_method == 'POST' and req.POST:
        form = input_form(req.POST)
    if form and form.is_valid():
        session = form.cleaned_data['transactionId']
        request_string = form.cleaned_data['ussdRequestString']
        response_content = ''
        action = None
        if session.error_case():
            response_content, action = __render_screen_from_session__(session)
        elif not session.current_xform:
            if request_string:
                try:
                    if request_string == '#':
                        session.back()
                    elif request_string == 'continue' and not session.current_menu_item.parent:
                        pass
                    else:
                        order = int(request_string)
                        order = session.current_menu_item.get_nth_item(order)
                        session.advance_menu_progress(order)
                except ValueError:
                    response_content = "Invalid Menu Option.\n"

        elif session.current_xform:
            if session.is_skip_prompt:
                try:
                    choice = int(request_string)
                    if choice == 1:
                        # Done with the skip prompt, user wants to continue
                        session.is_skip_prompt = False
                        session.save()
                    elif choice == 2:
                        response_content = session.current_xform.response
                        session.submission.has_errors = False
                        session.submission.save()
                        action = 'end'
                    else:
                        response_content = "Invalid Menu Option.\n"
                except ValueError:
                    response_content = "Invalid Menu Option.\n"
            else:
                try:
                    if not session.process_xform_response(request_string):
                        response_content = session.submission.response
                        action = 'end'
                except ValidationError, e:
                    response_content = "\n".join(e.messages)

        if not action:
            response, action = __render_screen_from_session__(session)
            response_content += response

        return render_to_response(output_template, {
            'response_content':urllib.quote(response_content),
            'action':action,
        }, context_instance=RequestContext(req))

    return HttpResponse(status=404)

