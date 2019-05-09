from django.db import models
from django.db.models import Count

from .fields import CharField

__all__ = ['Chat', 'Message', 'Button', 'Reaction', 'Keyboard']


class KeyboardManager(models.Manager):
    def create_with_buttons(self, buttons):
        k = self.create()
        Button.objects.bulk_create([
            Button(keyboard=k, index=i, text=b) for i, b in enumerate(buttons)
        ])
        return k

    def get_default(self):
        """Get first created keyboard, if absent - create one in place."""
        k = self.order_by('id').first()
        if k:
            return k
        return self.create_with_buttons(['👍', '👎'])


class Keyboard(models.Model):
    objects = KeyboardManager()

    @property
    def buttons(self):
        return [b.text for b in self.button_set.all()]

    def copy(self):
        k = Keyboard.objects.create()
        bs = list(self.button_set.all())
        for b in bs:
            b.id = None
            b.keyboard = k
        Button.objects.bulk_create(bs)
        return k

    def __str__(self):
        bs = ', '.join(self.buttons)
        return f"Keyboard({self.id}, {bs})"


class Button(models.Model):
    keyboard = models.ForeignKey(Keyboard, on_delete=models.CASCADE)
    index = models.IntegerField()
    text = CharField(max_length=100)

    class Meta:
        unique_together = ('keyboard', 'text')
        ordering = ('index',)


class Chat(models.Model):
    id = CharField(unique=True, primary_key=True, help_text="Telegram chat ID.")
    keyboard = models.ForeignKey(Keyboard, on_delete=models.CASCADE)

    def set_keyboard(self, buttons):
        self.keyboard = Keyboard.objects.create_with_buttons(buttons)
        self.save()

    def save(self, *args, **kwargs):
        if not self.keyboard_id:
            self.keyboard = Keyboard.objects.get_default()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Chat({self.id}, {self.keyboard})"


class MessageManager(models.Manager):
    def create(self, chat_id, message_id, **kwargs):
        """Create message based on chat ID and original telegram message ID."""
        umid = Message.get_id(chat_id, message_id)
        return super().create(id=umid, chat_id=chat_id, **kwargs)


class Message(models.Model):
    id = CharField(
        unique=True,
        primary_key=True,
        help_text="Telegram message ID merged with chat ID.",
    )
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    keyboard = models.OneToOneField(Keyboard, on_delete=models.CASCADE)

    objects = MessageManager()

    @classmethod
    def get_id(cls, chat_id, message_id):
        """merge chat_id and message_id to create globally unique Message ID"""
        if Message.is_id(message_id):
            return message_id
        return Message.make_id(chat_id, message_id)

    @classmethod
    def make_id(cls, chat_id, message_id):
        return f'{chat_id}~{message_id}'

    @classmethod
    def is_id(cls, m_id):
        return isinstance(m_id, str) and '~' in m_id

    def reactions(self):
        rs = self.reaction_set.all()
        return rs.values('button').annotate(count=Count('id'))

    def save(self, *args, **kwargs):
        # get default chat keyboard if not specified
        if not self.keyboard_id:
            self.keyboard = self.chat.keyboard.copy()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"<Message {self.chat_id} {self.id}>"


class ReactionManager(models.Manager):
    def react(self, user_id, chat_id, message_id, button_id):
        """
        Add user reaction to the message.
        If reaction is the same - remove old reaction.
        If user already reacted to this message with another button - change button.

        Message-Button consistency should be guarantied by Telegram API.
        """
        univ_message_id = Message.get_id(chat_id, message_id)
        try:
            r = Reaction.objects.get(
                user_id=user_id,
                message_id=univ_message_id,
            )
            # user already reacted...
            # clicked same button -> remove reaction
            if r.button_id == button_id:
                r.delete()
                return None
            # clicked another button -> change reaction
            r.button_id = button_id
            r.save()
            return r
        except Reaction.DoesNotExist:
            # user reacting first time
            return Reaction.objects.create(
                user_id=user_id,
                message_id=univ_message_id,
                button_id=button_id,
            )


class Reaction(models.Model):
    user_id = CharField(help_text="Telegram user ID.")
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    button = models.ForeignKey(Button, on_delete=models.CASCADE)

    objects = ReactionManager()

    class Meta:
        unique_together = ('user_id', 'message')

    def __str__(self):
        return f"<R {self.user_id} {self.message_id} {self.button.text}>"
