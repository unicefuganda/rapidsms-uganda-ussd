from django.http import HttpResponse

def ussd(req):
    return HttpResponse(content='responseString=Hello%2C+World%21&action=end', status=200)
