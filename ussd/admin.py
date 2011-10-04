from django.contrib import admin
from .models import USSDSession, MenuItem

admin.site.register(MenuItem)
admin.site.register(USSDSession)


