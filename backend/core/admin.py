from django.contrib import admin

from .models import Chat, Message

admin.site.register([Chat, Message])
