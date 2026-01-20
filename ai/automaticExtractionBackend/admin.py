# """
#  @file: admin.py
#  @Time    : 2025/3/30
#  @Author  : Peinuan qin
#  """
# from django.contrib import admin
#
# from automaticExtractionBackend.models import SystemUser, Entity, Sentence, Triple
#
# @admin.register(SystemUser)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('pk', 'username', 'email')
#     search_fields = ('email',)
#     ordering = ('email',)
#
#
#
# @admin.register(Entity)
# class EntityAdmin(admin.ModelAdmin):
#     list_display = ('pk', 'name', 'construct')
#     search_fields = ('name', 'construct')
#
#
# @admin.register(Sentence)
# class SentenceAdmin(admin.ModelAdmin):
#     list_display = ('pk', 'text',)
#     search_fields = ('text',)
#     filter_horizontal = ('entities',)  # 多对多字段显示更友好
#
#
# @admin.register(Triple)
# class TripleAdmin(admin.ModelAdmin):
#     list_display = ('pk', 'sentence', 'start_entity', 'end_entity')
#     search_fields = ('sentence__text', 'start_entity__name', 'end_entity__name')
#     autocomplete_fields = ('sentence', 'start_entity', 'end_entity')
#
# # admin.site.register(SystemUser, UserAdmin)



"""
 @file: admin.py
 @Time    : 2025/3/30
 @Author  : Peinuan qin
"""
from django.contrib import admin
from automaticExtractionBackend.models import SystemUser, Construct, Entity, Sentence, Triple


@admin.register(SystemUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ('pk', 'username', 'email')
    search_fields = ('email',)
    ordering = ('email',)


@admin.register(Construct)
class ConstructAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'user')
    # search_fields = ('name', 'user__email')
    search_fields = ('name',)
    autocomplete_fields = ('user',)





@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ('pk', 'text', 'user', 'line_number')
    search_fields = ('text', 'user__email')
    autocomplete_fields = ('user',)


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'construct', 'user', 'canonical_entity','sentence', 'color')
    search_fields = ('name', 'construct', 'user__email', 'sentence__text')
    autocomplete_fields = ('user', 'sentence', 'canonical_entity')


@admin.register(Triple)
class TripleAdmin(admin.ModelAdmin):
    list_display = ('pk', 'sentence', 'entity_cause', 'entity_effect', 'user')
    search_fields = ('sentence__text', 'entity_cause__name', 'entity_effect__name', 'user__email')
    autocomplete_fields = ('sentence', 'entity_cause', 'entity_effect', 'user')
