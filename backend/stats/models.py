from typing import Union

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from core.models import Chat, Button


class PopularReactions(models.Model):
    chat = models.OneToOneField(Chat, on_delete=models.CASCADE)
    updated = models.DateTimeField()

    @classmethod
    def get(cls, chat: Union[Chat, int]):
        if isinstance(chat, Chat):
            chat = chat.id

        root, _ = PopularReactions.objects.get_or_create(
            chat_id=chat,
            defaults={'updated': timezone.now()},
        )
        if root.expired:
            return root.calculate()
        return root.reaction_set.all()

    @property
    def expired(self) -> bool:
        return self.updated + settings.STATS_EXPIRATION_DELTA < timezone.now()

    def calculate(self):
        self.reaction_set.all().delete()

        qs = Button.objects.filter(message__chat__id=self.chat_id)
        qs = qs.values('text')
        qs = qs.annotate(Sum('count'))
        qs = qs.order_by('-count__sum')
        qs = qs[:settings.STATS_MAX_RESULTS]

        return Reaction.objects.bulk_create([
            Reaction(root=self, text=e['text'], count=e['count__sum'])
            for e in qs
        ])


class Reaction(models.Model):
    root = models.ForeignKey(PopularReactions, on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    count = models.IntegerField()

    def __str__(self):
        return f"R({self.text}, {self.count})"

    class Meta:
        ordering = ('-count',)
