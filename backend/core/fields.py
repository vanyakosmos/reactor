from django.db import models
from django import forms


class CharField(models.TextField):
    def formfield(self, **kwargs):
        kwargs['widget'] = forms.TextInput
        return super(CharField, self).formfield(**kwargs)
