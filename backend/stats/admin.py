from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import PopularReactions, Reaction, TopPosters, Poster


def recalculate(model_admin, request, queryset):
    for obj in queryset:
        obj.calculate()


recalculate.short_description = "Recalculate stats"


class ExpiredMixin:
    def expired(self, stats):
        return stats.expired

    expired.boolean = True


class ReactionInline(admin.TabularInline):
    model = Reaction
    fields = ('text', 'count')
    extra = 0


@admin.register(PopularReactions)
class PopularReactionsAdmin(ExpiredMixin, admin.ModelAdmin):
    list_display = ('chat', 'updated', 'expired', 'top3')
    fields = ('chat', 'updated', 'expired', 'reactions')
    readonly_fields = ('expired', 'reactions')
    inlines = (ReactionInline,)
    actions = (recalculate,)

    def prettify(self, qs):
        lines = [f"{i + 1:2d}. {r.text} -> {r.count}" for i, r in enumerate(qs)]
        text = '\n'.join(lines)
        return mark_safe(f'<pre style="margin: 0; padding: 0">{text}</pre>')

    def top3(self, pr: PopularReactions):
        qs = pr.items.all()[:3]
        return self.prettify(qs)

    def reactions(self, pr: PopularReactions):
        qs = pr.items.all()
        return self.prettify(qs)


class PosterInline(admin.TabularInline):
    model = Poster
    fields = ('user', 'messages', 'reactions')
    extra = 0


@admin.register(TopPosters)
class TopPostersAdmin(ExpiredMixin, admin.ModelAdmin):
    list_display = ('chat', 'updated', 'expired', 'top3')
    fields = ('chat', 'updated', 'expired', 'top_posters')
    readonly_fields = ('expired', 'top_posters')
    inlines = (PosterInline,)
    actions = (recalculate,)

    def prettify(self, qs):
        lines = [
            f"{i + 1:2d}. {p.user.full_name} -> reactions: {p.reactions}, messages: {p.messages}"
            for i, p in enumerate(qs)
        ]
        text = '\n'.join(lines)
        return mark_safe(f'<pre style="margin: 0; padding: 0">{text}</pre>')

    def top3(self, tp: TopPosters):
        qs = tp.items.all()[:3]
        return self.prettify(qs)

    def top_posters(self, tp: TopPosters):
        qs = tp.items.all()
        return self.prettify(qs)
