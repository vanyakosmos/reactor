from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import Chat, Message, User


@admin.register(Chat)
class ChatAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'title', 'type', 'get_buttons')
    list_filter = (
        'type',
        'show_credits',
        'add_padding',
        'allow_reactions',
        'force_emojis',
        'repost',
    )
    search_fields = ('id', 'username', 'title')

    def get_buttons(self, chat: Chat):
        return '/'.join(chat.buttons)

    get_buttons.short_description = 'Buttons'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat', 'date', 'from_user', 'get_buttons')
    ordering = ('-date',)

    def get_buttons(self, msg: Message):
        return '/'.join([b.text for b in msg.button_set.all()])

    get_buttons.short_description = 'Buttons'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'first_name', 'last_name', 'get_url')
    search_fields = ('id', 'username', 'first_name', 'last_name')

    def get_url(self, user: User):
        url = user.url
        if url:
            return mark_safe(f'<a href="{url}" target="_blank">link</a>')

    get_url.short_description = 'TG Url'
