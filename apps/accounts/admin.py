from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import Membership, User

admin.site.register(User, UserAdmin)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "workshop", "role"]
    list_filter = ["role"]
    list_select_related = ["user", "workshop"]
