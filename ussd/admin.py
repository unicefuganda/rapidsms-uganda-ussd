from django.contrib import admin
from .models import Screen, Menu, Question, Field
from mptt.admin import MPTTModelAdmin

admin.site.register(Screen, MPTTModelAdmin)
admin.site.register(Question, MPTTModelAdmin)
admin.site.register(Field, MPTTModelAdmin)
admin.site.register(Menu, MPTTModelAdmin)



