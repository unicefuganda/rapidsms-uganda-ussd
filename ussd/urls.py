from django.conf.urls.defaults import *
from . import views

urlpatterns = patterns('',
    url(r"^ussd/$", views.ussd, name="ussd-gateway"),
)
