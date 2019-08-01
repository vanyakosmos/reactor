import uuid
from typing import Tuple, List

from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import IntegrityError, models
from django.utils import timezone
from telegram import Chat as TGChat, Message as TGMessage, Update, User as TGUser

from bot.consts import MAX_NUM_BUTTONS, MAX_USER_BUTTONS_HINTS
from .fields import CharField

__all__ = ['Chat', 'Message', 'Button', 'Reaction', 'User', 'UserButtons', 'MessageToPublish']


class TGMixin:
    @property
    def tg(self):
        raise NotImplemented

    def tgb(self, bot):
        tg_obj = self.tg
        tg_obj.bot = bot
        return tg_obj


class UserManager(models.Manager):
    def from_tg_user(self, u: TGUser) -> 'User':
        user, _ = User.objects.update_or_create(
            id=u.id,
            defaults={
                'username': u.username,
                'first_name': u.first_name,
                'last_name': u.last_name,
            },
        )
        return user

    def from_update(self, update: Update):
        u = update.effective_user
        return self.from_tg_user(u)


class User(TGMixin, models.Model):
    """Telegram user or chat that hold information about original message sender."""
    id = CharField(unique=True, primary_key=True, help_text="Telegram user ID.")
    username = CharField(blank=True, null=True)
    first_name = CharField()
    last_name = CharField(blank=True, null=True)

    objects = UserManager()

    @property
    def full_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        if self.username:
            return self.username
        return self.first_name

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

    def __str__(self):
        return f"User({self.id}, {self.full_name})"


class ChatManager(models.Manager):
    def from_tg_chat(self, tg_chat: TGChat) -> 'Chat':
        if tg_chat.last_name:
            fallback_name = f'{tg_chat.first_name} {tg_chat.last_name}'
        else:
            fallback_name = tg_chat.first_name
        chat, _ = Chat.objects.update_or_create(
            id=tg_chat.id,
            defaults={
                'type': tg_chat.type,
                'username': tg_chat.username,
                'title': tg_chat.title or fallback_name,
            },
        )
        return chat

    def from_update(self, update: Update):
        chat = update.effective_chat
        return self.from_tg_chat(chat)


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
    add_padding = models.BooleanField(default=False)
    columns = models.IntegerField(default=4)
    allowed_types = ArrayField(models.CharField(max_length=100), default=default_allowed_types)
    allow_reactions = models.BooleanField(default=True)
    force_emojis = models.BooleanField(default=False)
    repost = models.BooleanField(default=True)

    objects = ChatManager()

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

    def __str__(self):
        name = self.title or self.username
        buttons = '/'.join(self.buttons)
        return f"Chat({self.id}, {name!r}, {buttons})"


class MessageQuerySet(models.QuerySet):
    def get_by_ids(self, chat_id, message_id, inline_message_id=None) -> 'Message':
        umid = Message.get_id(chat_id, message_id, inline_message_id)
        return self.get(id=umid)

    def create_from_inline(
        self, inline_message_id, from_user: User, buttons: list, **kwargs
    ) -> 'Message':
        """
        Create message based on inline_message_id.
        Populate buttons.
        """
        msg = self.create(
            id=inline_message_id,
            from_user=from_user,
            date=timezone.now(),
            inline_message_id=inline_message_id,
            **kwargs,
        )
        msg.set_buttons(buttons)
        return msg

    def create_from_tg_ids(
        self, chat_id, message_id, date, from_user: User, buttons=None, **kwargs
    ) -> 'Message':
        """
        Create message based on chat ID and original telegram message ID.
        Populate buttons.
        """
        umid = Message.get_id(chat_id, message_id)
        msg = self.create(id=umid, chat_id=chat_id, date=date, from_user=from_user, **kwargs)
        buttons = msg.chat.buttons if buttons is None else buttons
        msg.set_buttons(buttons)
        return msg


class Message(TGMixin, models.Model):
    id = CharField(
        unique=True,
        primary_key=True,
        help_text="Telegram message ID merged with chat ID.",
    )
    date = models.DateTimeField()
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, null=True)
    anonymous = models.BooleanField(default=False)
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
        if self.inline_message_id:
            return {
                'chat_id': None,
                'message_id': None,
                'inline_message_id': self.inline_message_id,
            }
        return {
            'chat_id': self.chat_id,
            'message_id': self.message_id,
            'inline_message_id': None,
        }

    @property
    def message_id(self):
        parts = self.id.split('_')
        if len(parts) == 2:
            return parts[1]

    @property
    def tg(self):
        return TGMessage(
            message_id=self.message_id or self.id,
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

    @property
    def is_inline(self):
        return self.id == self.inline_message_id

    def set_buttons(self, buttons, permanent=True):
        Button.objects.bulk_create([
            Button(message=self, index=index, text=text, permanent=permanent)
            for index, text in enumerate(buttons)
        ])

    def __str__(self):
        ids = ', '.join(map(lambda e: f'{e[0]}={e[1]}', self.ids.items()))
        return f"Message({self.id}, {ids})"


class ButtonManager(models.Manager):
    def get_for_reaction(self, reaction, umid):
        try:
            return Button.objects.get(message_id=umid, text=reaction)
        except Button.DoesNotExist:
            b = self.filter(message_id=umid).last()
            index = b.index + 1 if b else 0
            if index < MAX_NUM_BUTTONS:
                return Button.objects.create(message_id=umid, text=reaction, index=index)

    def reactions(self, chat_id, message_id, inline_message_id=None) -> List[Tuple[str, int]]:
        umid = Message.get_id(chat_id, message_id, inline_message_id)
        buttons = self.filter(message_id=umid).order_by('index')
        return list(buttons.values_list('text', 'count'))


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
        elif self.count >= 1:
            self.count -= 1
            self.save()

    def __str__(self):
        return f"B({self.text} {self.count})"

    class Meta:
        unique_together = ('message', 'text')
        ordering = ('index',)


class ReactionManager(models.Manager):
    def safe_create(self, user: TGUser, umid, button: Button, rerun=True):
        try:
            return Reaction.objects.create(
                user_id=user.id,
                message_id=umid,
                button=button,
            )
        except IntegrityError:
            User.objects.from_tg_user(user)
            if rerun:
                return self.safe_create(user, umid, button, rerun=False)
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
        if not button:
            # too many buttons
            return None, None
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


class MessageToPublish(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = JSONField()
    buttons = ArrayField(CharField(), null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def last(cls, user_id):
        return MessageToPublish.objects.filter(user_id=user_id).last()

    @property
    def message_tg(self) -> TGMessage:
        return TGMessage.de_json(self.message, None)

    class Meta:
        ordering = ('created',)


class UserButtons(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    buttons = ArrayField(CharField())
    created = models.DateTimeField(auto_now_add=True)

    @classmethod
    def delete_old(cls, user_id):
        ubs = UserButtons.objects.filter(user_id=user_id)
        ubs = ubs[:MAX_USER_BUTTONS_HINTS].values_list('id', flat=True)
        UserButtons.objects.exclude(pk__in=list(ubs)).delete()

    @classmethod
    def create(cls, user_id, buttons):
        buttons = buttons[:MAX_NUM_BUTTONS]
        if not UserButtons.objects.filter(user_id=user_id, buttons=buttons).exists():
            ub = UserButtons.objects.create(user_id=user_id, buttons=buttons)
            cls.delete_old(user_id)
            return ub

    @classmethod
    def buttons_list(cls, user_id):
        ubs = UserButtons.objects.filter(user_id=user_id)
        return [ub.buttons_str for ub in ubs]

    @property
    def buttons_str(self):
        return ' '.join(self.buttons)

    class Meta:
        ordering = ('-created',)
