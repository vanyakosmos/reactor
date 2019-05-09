import sys

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = 'core'
    verbose_name = 'Core App'

    def ready(self):
        try:
            from core.models import Keyboard
            Keyboard.objects.get_default()
        except Exception as e:
            print(e, file=sys.stderr)
