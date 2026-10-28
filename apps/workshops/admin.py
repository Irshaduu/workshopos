from django.contrib import admin

from apps.workshops.models import Branch, Workshop


@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ["name", "short_code", "status"]
    list_filter = ["status"]

    def get_readonly_fields(self, request, obj=None):
        # A short code is set when the workshop is made and never changed:
        # every username of the workshop starts with it (SIGN-8).
        return ["short_code"] if obj else []


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "workshop"]
    list_select_related = ["workshop"]
