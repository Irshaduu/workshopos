from django.contrib import admin

from apps.workshops.models import Branch, Workshop


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ["name", "status"]
    list_filter = ["status"]


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "workshop"]
    list_select_related = ["workshop"]
