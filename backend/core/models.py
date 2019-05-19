from django.contrib.postgres.fields import ArrayField
from django.db import models

from .fields import CharField

__all__ = ['Chat', 'Message', 'Button', 'Reaction', 'TGUser']


class TGUser(models.Model):
    """Telegram user or chat that hold information about original message sender."""
    id = CharField(unique=True, primary_key=True, help_text="Telegram user ID.")
    username = CharField(blank=True, null=True)
    name = CharField()

    @property
    def url(self):
        if self.username:
            return f'https://t.me/{self.username}'


def default_buttons():
    return ['👍', '👎']


def default_allowed_types():
    return ['photo', 'video', 'animation', 'link', 'forward']


class Chat(models.Model):
    id = CharField(unique=True, primary_key=True, help_text="Telegram chat ID.")
    buttons = ArrayField(models.CharField(max_length=100), default=default_buttons)
    show_credits = models.BooleanField(default=True)
    add_padding = models.BooleanField(default=True)
    columns = models.IntegerField(default=4)
    allowed_types = ArrayField(models.CharField(max_length=100), default=default_allowed_types)

    def reactions(self):
        return [{
            'index': index,
            'text': text,
            'count': 0,
        } for index, text in enumerate(self.buttons)]

    def __str__(self):
        return f"Chat({self.id}, {self.buttons})"


class MessageManager(models.Manager):
    def get_by_ids(self, chat_id, message_id):
        umid = Message.get_id(chat_id, message_id)
        return Message.objects.get(id=umid)

    def create(self, chat_id, message_id, **kwargs):
        """
        Create message based on chat ID and original telegram message ID.
        Populate buttons.
        """
        umid = Message.get_id(chat_id, message_id)
        msg = super().create(id=umid, chat_id=chat_id, **kwargs)
        Button.objects.bulk_create([
            Button(message=msg, index=index, text=text, permanent=True)
            for index, text in enumerate(msg.chat.buttons)
        ])
        return msg


class Message(models.Model):
    id = CharField(
        unique=True,
        primary_key=True,
        help_text="Telegram message ID merged with chat ID.",
    )
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    original_message_id = CharField(
        help_text="Telegram ID of original message w/o appended chat ID."
    )
    forward_from_message_id = CharField(
        blank=True,
        null=True,
        help_text="Telegram ID of original forwarded message w/o appended chat ID."
    )
    from_user = models.ForeignKey(
        TGUser,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    from_forward = models.ForeignKey(
        TGUser,
        on_delete=models.SET_NULL,
        related_name='forward_messages',
        blank=True,
        null=True,
    )

    objects = MessageManager()

    @property
    def from_url(self):
        return self.from_user.url

    @property
    def from_forward_url(self):
        if self.from_forward:
            base_url = self.from_forward.url
            if base_url:
                return f'{base_url}/{self.forward_from_message_id}'

    @classmethod
    def get_id(cls, chat_id, message_id):
        """merge chat_id and message_id to create globally unique Message ID"""
        if isinstance(message_id, str) and '~' in message_id:
            return message_id
        return f'{chat_id}~{message_id}'

    def __str__(self):
        return f"Message({self.id})"


class ButtonManager(models.Manager):
    def filter_by_message(self, chat_id, message_id):
        umid = Message.get_id(chat_id, message_id)
        return self.filter(message_id=umid)

    def reactions(self, chat_id, message_id):
        return [{
            'id': b.id,
            'index': b.index,
            'text': b.text,
            'count': b.count,
        } for b in self.filter_by_message(chat_id, message_id)]


class Button(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    index = models.IntegerField()
    text = CharField(max_length=100)
    count = models.IntegerField(default=0)
    permanent = models.BooleanField(default=False)

    objects = ButtonManager()

    def inc(self):
        self.count += 1
        self.save()

    def dec(self):
        if self.count == 1 and not self.permanent:
            self.delete()
        else:
            self.count -= 1
            self.save()

    def __str__(self):
        return f"B({self.text} {self.count})"

    class Meta:
        unique_together = ('message', 'text')
        ordering = ('index',)


class ReactionManager(models.Manager):
    def react(self, user_id, chat_id, message_id, button_text):
        """
        Add user reaction to the message.
        If reaction is the same - remove old reaction.
        If user already reacted to this message with another button - change button.

        Message-Button consistency should be guarantied by Telegram API.
        """
        univ_message_id = Message.get_id(chat_id, message_id)
        button = Button.objects.get(message__id=univ_message_id, text=button_text)
        try:
            r = Reaction.objects.get(
                user_id=user_id,
                message_id=univ_message_id,
            )
            # user already reacted...
            # clicked same button -> remove reaction
            if r.button_id == button.id:
                r.delete()
                r = None
                button.dec()
            else:
                # clicked another button -> change reaction
                old_btn = r.button
                old_btn.dec()
                button.inc()
                r.button = button
                r.save()
        except Reaction.DoesNotExist:
            # user reacting first time
            r = Reaction.objects.create(
                user_id=user_id,
                message_id=univ_message_id,
                button=button,
            )
            button.inc()
        return r, button


class Reaction(models.Model):
    user = models.ForeignKey(TGUser, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    button = models.ForeignKey(Button, on_delete=models.CASCADE)

    objects = ReactionManager()

    class Meta:
        unique_together = ('user', 'message')

    def __str__(self):
        return f"R({self.user_id} {self.message_id} {self.button.text})"
