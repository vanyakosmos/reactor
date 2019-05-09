from django.db import models
from django import forms


class CharField(models.TextField):
    def formfield(self, **kwargs):
        return super(CharField, self).formfield(widget=forms.TextInput, **kwargs)
