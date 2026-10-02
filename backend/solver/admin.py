from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import SolveSession, AgentEvent

admin.site.register(SolveSession)
admin.site.register(AgentEvent)