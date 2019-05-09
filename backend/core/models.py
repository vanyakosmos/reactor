from django.db import models
from django.db.models import Count

from .fields import CharField

__all__ = ['Chat', 'Message', 'Button', 'Reaction', 'Keyboard']


class KeyboardManager(models.Manager):
    def create_with_buttons(self, buttons):
        k = Keyboard.objects.create()
        Button.objects.bulk_create([
            Button(keyboard=k, index=i, text=b) for i, b in enumerate(buttons)
        ])
        return k

    def create_default(self):
        return self.create_with_buttons(['👍', '👎'])


class Keyboard(models.Model):
    objects = KeyboardManager()


class Button(models.Model):
    keyboard = models.ForeignKey(Keyboard, on_delete=models.CASCADE)
    index = models.IntegerField()
    text = CharField(max_length=100)


class Chat(models.Model):
    chat_id = CharField(unique=True, primary_key=True)
    keyboard = models.OneToOneField(Keyboard, on_delete=models.CASCADE)

    def set_keyboard(self, buttons):
        self.keyboard = Keyboard.objects.create_with_buttons(buttons)
        self.save()


class Message(models.Model):
    message_id = CharField(unique=True, primary_key=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    keyboard = models.ForeignKey(Keyboard, on_delete=models.CASCADE)

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

    class Meta:
        unique_together = ('chat', 'message_id')

    def save(self, *args, **kwargs):
        self.message_id = Message.get_id(self.chat_id, self.message_id)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"<Message {self.chat_id} {self.message_id}>"


class ReactionManager(models.Manager):
    def react(self, user_id, chat_id, message_id, button_id):
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
    user_id = CharField()
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    button = models.ForeignKey(Button, on_delete=models.CASCADE)

    objects = ReactionManager()

    class Meta:
        unique_together = ('user_id', 'message')

    def __str__(self):
        return f"<R {self.user_id} {self.message_id} {self.button.text}>"
