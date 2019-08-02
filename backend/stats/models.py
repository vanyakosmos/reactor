from typing import Union

from django.conf import settings
from django.db import models
from django.db.models import Sum, Count
from django.utils import timezone

from core.models import Chat, Button, User, Message


class Stats(models.Model):
    chat = models.OneToOneField(Chat, on_delete=models.CASCADE)
    updated = models.DateTimeField()

    @classmethod
    def get(cls, chat: Union[Chat, int]):
        if isinstance(chat, Chat):
            chat = chat.id

        root, _ = cls.objects.get_or_create(
            chat_id=chat,
            defaults={'updated': timezone.now()},
        )
        if root.expired:
            return root.calculate()
        return root.items.all()

    @property
    def expired(self):
        if not self.updated:
            return
        return self.updated + settings.STATS_EXPIRATION_DELTA < timezone.now()

    def calculate(self):
        raise NotImplementedError

    def save(self, *args, **kwargs):
        if not self.updated:
            self.updated = timezone.now()
        return super().save(*args, **kwargs)

    def __str__(self):
        cls = self.__class__.__name__
        return f"{cls}({self.chat}, {self.updated})"

    class Meta:
        abstract = True


class PopularReactions(Stats):
    def calculate(self):
        """
        { button_text: button_count, ... }
        for message in chat:
            for button in message:
                result[button.text] += button.count
        """
        self.items.all().delete()

        qs = Button.objects.filter(message__chat__id=self.chat_id)
        qs = qs.distinct()
        qs = qs.values('text')
        qs = qs.annotate(Sum('count'))
        qs = qs.order_by('-count__sum')
        qs = qs[:settings.STATS_MAX_RESULTS]

        return Reaction.objects.bulk_create([
            Reaction(root=self, text=e['text'], count=e['count__sum'])
            for e in qs
        ])

    class Meta:
        verbose_name = "Popular Reactions"
        verbose_name_plural = verbose_name


class Reaction(models.Model):
    root = models.ForeignKey(PopularReactions, on_delete=models.CASCADE, related_name='items')
    text = models.CharField(max_length=100)
    count = models.IntegerField()

    def __str__(self):
        return f"R({self.text}, {self.count})"

    class Meta:
        ordering = ('-count',)


class TopPosters(Stats):
    def calculate(self):
        """
        { user: { messages: X, reactions: Y } }
        for message in chat:
            results[message_user][messages] += 1
            for button in message:
                results[message_user][reaction] += button.count
        """
        self.items.all().delete()

        qs = Message.objects.filter(chat_id=self.chat_id)
        qs = qs.values('from_user')
        qs = qs.annotate(messages=Count('id', distinct=True))
        qs = qs.annotate(reactions=Sum('button__count'))
        qs = qs.order_by('-reactions', '-messages')
        qs = qs[:settings.STATS_MAX_RESULTS]

        return Poster.objects.bulk_create([
            Poster(
                root=self,
                user_id=e['from_user'],
                messages=e['messages'],
                reactions=e['reactions'],
            ) for e in qs
        ])

    class Meta:
        verbose_name = "Top Posters"
        verbose_name_plural = verbose_name


class Poster(models.Model):
    root = models.ForeignKey(TopPosters, on_delete=models.CASCADE, related_name='items')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    messages = models.IntegerField(help_text="Number of messages posted by user.")
    reactions = models.IntegerField(help_text="Number of reactions on user's posts.")

    def __str__(self):
        return f"Poster({self.user.full_name}, m={self.messages}, r={self.reactions})"

    class Meta:
        ordering = ('-reactions', '-messages')
