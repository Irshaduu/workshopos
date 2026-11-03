"""The tab bar and the menu, for templates/app.html (ROLE-23)."""

from django import template

from apps.accounts import menu as role_menus

register = template.Library()


@register.inclusion_tag("components/tab_bar.html", takes_context=True)
def tab_bar(context):
    return role_menus.tab_bar(context["request"])


@register.inclusion_tag("components/menu.html", takes_context=True)
def menu(context):
    return role_menus.menu(context["request"])
