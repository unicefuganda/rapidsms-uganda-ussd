from .forms import YoForm
from django.http import HttpResponse

def ussd(req):
    form = YoForm(req.GET)
    if form.is_valid():
        pass
    return HttpResponse(content='responseString=Hello%2C+World%21&action=end', status=200)
