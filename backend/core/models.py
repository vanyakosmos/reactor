from django.contrib.postgres.fields import ArrayField
from django.db import models, IntegrityError
from django.utils import timezone
from telegram import Chat as TGChat, Message as TGMessage, User as TGUser

from .fields import CharField

__all__ = ['Chat', 'Message', 'Button', 'Reaction', 'User']


class TGMixin:
    @property
    def tg(self):
        raise NotImplemented

    def tgb(self, bot):
        tg_obj = self.tg
        tg_obj.bot = bot
        return tg_obj


class UserManager(models.Manager):
    def create_from_tg_user(self, u: TGUser):
        user, _ = User.objects.update_or_create(
            id=u.id,
            defaults={
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
            },
        )
        return user


class User(TGMixin, models.Model):
    """Telegram user or chat that hold information about original message sender."""
    id = CharField(unique=True, primary_key=True, help_text="Telegram user ID.")
    username = CharField(blank=True, null=True)
    first_name = CharField()
    last_name = CharField(blank=True, null=True)

    objects = UserManager()

    @property
    def tg(self):
        return TGUser(
            id=self.id,
            first_name=self.first_name,
            last_name=self.last_name,
            username=self.username,
            is_bot=False,
        )

    @property
    def url(self):
        if self.username:
            return f'https://t.me/{self.username}'


def default_buttons():
    return ['👍', '👎']


def default_allowed_types():
    return ['photo', 'video', 'animation', 'link', 'forward']


class Chat(TGMixin, models.Model):
    id = CharField(unique=True, primary_key=True, help_text="Telegram chat ID.")
    title = CharField(blank=True, null=True)
    username = CharField(blank=True, null=True)
    type = CharField()
    buttons = ArrayField(models.CharField(max_length=100), default=default_buttons)
    show_credits = models.BooleanField(default=True)
    add_padding = models.BooleanField(default=True)
    columns = models.IntegerField(default=4)
    allowed_types = ArrayField(models.CharField(max_length=100), default=default_allowed_types)

    @property
    def url(self):
        if self.username:
            return f'https://t.me/{self.username}'

    @property
    def tg(self):
        return TGChat(
            id=self.id,
            type=self.type,
            title=self.title,
            username=self.username,
        )

    def reactions(self):
        return [{
            'index': index,
            'text': text,
            'count': 0,
        } for index, text in enumerate(self.buttons)]

    def __str__(self):
        return f"Chat({self.id}, {self.buttons})"


class MessageQuerySet(models.QuerySet):
    def get_by_ids(self, chat_id, message_id, inline_message_id=None):
        umid = Message.get_id(chat_id, message_id, inline_message_id)
        return Message.objects.get(id=umid)

    def create_from_inline(self, inline_message_id, buttons, **kwargs):
        """
        Create message based on inline_message_id.
        Populate buttons.
        """
        msg = self.create(
            id=inline_message_id,
            date=timezone.now(),
            inline_message_id=inline_message_id,
            **kwargs,
        )
        Button.objects.bulk_create([
            Button(message=msg, index=index, text=text, permanent=True)
            for index, text in enumerate(buttons)
        ])
        return msg

    def create_from_tg_ids(self, chat_id, message_id, **kwargs):
        """
        Create message based on chat ID and original telegram message ID.
        Populate buttons.
        """
        umid = Message.get_id(chat_id, message_id)
        msg = self.create(id=umid, chat_id=chat_id, **kwargs)
        Button.objects.bulk_create([
            Button(message=msg, index=index, text=text, permanent=True)
            for index, text in enumerate(msg.chat.buttons)
        ])
        return msg


class Message(TGMixin, models.Model):
    id = CharField(
        unique=True,
        primary_key=True,
        help_text="Telegram message ID merged with chat ID.",
    )
    date = models.DateTimeField()
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, null=True)
    original_message_id = CharField(
        blank=True, null=True, help_text="Telegram ID of original message w/o appended chat ID."
    )
    inline_message_id = CharField(
        blank=True,
        null=True,
        help_text="Telegram ID of inline message.",
    )
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    forward_from = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='forward_messages',
        blank=True,
        null=True,
    )
    forward_from_chat = models.ForeignKey(
        Chat,
        on_delete=models.SET_NULL,
        related_name='forward_messages',
        blank=True,
        null=True,
    )
    forward_from_message_id = CharField(
        blank=True,
        null=True,
        help_text="Telegram ID of original forwarded message w/o appended chat ID."
    )

    objects = MessageQuerySet.as_manager()

    @classmethod
    def get_id(cls, chat_id, message_id, inline_message_id=None):
        """merge chat_id and message_id to create globally unique Message ID"""
        if inline_message_id:
            return inline_message_id
        if message_id is None:
            return chat_id
        if isinstance(message_id, str) and '_' in message_id:
            return message_id
        return f'{chat_id}_{message_id}'

    @classmethod
    def split_id(cls, umid: str):
        return umid.split('_')

    @property
    def ids(self):
        return {
            'chat_id': self.chat_id,
            'message_id': self.message_id,
            'inline_message_id': self.inline_message_id,
        }

    @property
    def message_id(self):
        parts = self.id.split('_')
        if len(parts) == 2:
            return parts[1]

    @property
    def tg(self):
        return TGMessage(
            message_id=self.id,
            from_user=self.from_user.tg,
            date=self.date,
            chat=self.chat and self.chat.tg,
            forward_from=self.forward_from and self.forward_from.tg,
            forward_from_chat=self.forward_from_chat and self.forward_from_chat.tg,
            forward_from_message_id=self.forward_from_message_id,
        )

    def tgb(self, bot):
        obj = self.tg
        obj.bot = bot
        if obj.chat:
            obj.chat.bot = bot
        obj.from_user.bot = bot
        if obj.forward_from:
            obj.forward_from.bot = bot
        if obj.forward_from_chat:
            obj.forward_from_chat.bot = bot
        return obj

    @property
    def from_user_url(self):
        return self.from_user.url

    @property
    def forward_user_url(self):
        if self.forward_from:
            return self.forward_from.url

    @property
    def forward_chat_url(self):
        if self.forward_from_chat:
            base_url = self.forward_from_chat.url
            if base_url:
                return f'{base_url}/{self.forward_from_message_id}'

    def __str__(self):
        return f"Message({self.id})"


class ButtonManager(models.Manager):
    def filter_by_message(self, chat_id, message_id, inline_message_id=None):
        umid = Message.get_id(chat_id, message_id, inline_message_id)
        return self.filter(message_id=umid)

    def get_for_reaction(self, reaction, umid):
        try:
            return Button.objects.get(message_id=umid, text=reaction)
        except Button.DoesNotExist:
            b = self.filter(message_id=umid).last()
            index = b.index + 1 if b else 0
            return Button.objects.create(message_id=umid, text=reaction, index=index)

    def reactions(self, chat_id, message_id, inline_message_id=None):
        return [{
            'id': b.id,
            'index': b.index,
            'text': b.text,
            'count': b.count,
        } for b in self.filter_by_message(chat_id, message_id, inline_message_id)]


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
    def safe_create(self, user, umid, button, ran=False):
        try:
            return Reaction.objects.create(
                user_id=user.id,
                message_id=umid,
                button=button,
            )
        except IntegrityError:
            User.objects.create_from_tg_user(user)
            if not ran:
                return self.safe_create(user, umid, button, ran=True)
            raise

    def react(self, user: TGUser, chat_id, message_id, inline_message_id, button_text):
        """
        Add user reaction to the message.
        If reaction is the same - remove old reaction.
        If user already reacted to this message with another button - change button.

        Message-Button consistency should be guarantied by Telegram API.
        """
        umid = Message.get_id(chat_id, message_id, inline_message_id)
        button = Button.objects.get_for_reaction(button_text, umid)
        try:
            r = Reaction.objects.get(
                user_id=user.id,
                message_id=umid,
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
            r = self.safe_create(user, umid, button)
            button.inc()
        return r, button


class Reaction(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)
    button = models.ForeignKey(Button, on_delete=models.CASCADE)

    objects = ReactionManager()

    class Meta:
        unique_together = ('user', 'message')

    def __str__(self):
        return f"R({self.user_id} {self.message_id} {self.button.text})"
