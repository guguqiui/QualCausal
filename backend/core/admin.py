from django.contrib import admin
from .models import SystemUser, Construct, Sentence, Entity, Triple

def get_all_field_names(model, exclude_fields=None):
    exclude_fields = exclude_fields or []
    return [field.name for field in model._meta.fields if field.name not in exclude_fields]
#
# def get_all_field_names(model):
#     return [field.name for field in model._meta.fields]

@admin.register(SystemUser)
class SystemUserAdmin(admin.ModelAdmin):
    list_display = get_all_field_names(SystemUser)

@admin.register(Construct)
class ConstructAdmin(admin.ModelAdmin):
    list_display = get_all_field_names(Construct)

@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = get_all_field_names(Sentence)
#
# @admin.register(Entity)
# class EntityAdmin(admin.ModelAdmin):
#     list_display = get_all_field_names(Entity)

@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = get_all_field_names(Entity, exclude_fields=["embeddings"])


@admin.register(Triple)
class TripleAdmin(admin.ModelAdmin):
    list_display = get_all_field_names(Triple)