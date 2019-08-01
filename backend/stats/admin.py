from emoji import UNICODE_EMOJI
from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import PopularReactions, Reaction


def emoji_len(text: str):
    return len(text) + sum(1 if c in UNICODE_EMOJI else 0 for c in text)


class ReactionInline(admin.TabularInline):
    model = Reaction
    fields = ('text', 'count')
    extra = 0


@admin.register(PopularReactions)
class PopularReactionsAdmin(admin.ModelAdmin):
    list_display = ('chat', 'updated', 'expired', 'reactions')
    inlines = (ReactionInline,)
    actions = ('recalculate',)

    def expired(self, pr):
        return pr.expired

    expired.boolean = True

    def reactions(self, pr: PopularReactions):
        qs = pr.reaction_set.all()
        qs = list(qs)
        if not qs:
            return '-'
        lines = []
        s = max(1, min(5, 25 // max(len(r.text) for r in qs)))
        while qs:
            sub = qs[:s]
            qs = qs[s:]
            lines.append('  /  '.join([f"{r.text} -> {r.count}" for r in sub]))
        text = '\n'.join(lines)
        return mark_safe(f'<pre>{text}</pre>')

    def recalculate(self, request, queryset):
        for pr in queryset:
            pr.calculate()

    recalculate.short_description = "Recalculate reactions"
