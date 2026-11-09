"""Safe defaults from the first app: sign-in, a strict CSP, one language, a small admin, and
the htmx file as it was checked."""

import hashlib

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path


def plain_page(request):
    return HttpResponse("A page nobody marked public.")


urlpatterns = [path("plain/", plain_page)]

#: The only models in the Django admin, and why. The admin is for emergencies
#: (ADR-0023). A business record is never in it: it changes only through its
#: service, so the audit log and every rule run, and platform staff never read
#: a workshop's data (ADR-0007).
ADMIN_MODELS = {
    "accounts.User": "set up or turn off an account",
    "accounts.Membership": "an account's workshop and role",
    "auth.Group": "Django's own, for staff permissions; workshop roles are memberships",
    "workshops.Workshop": "suspend or rename a workshop",
    "workshops.Branch": "rename a branch",
}

#: The htmx file kept in the repo (ADR-0016): `dist/htmx.min.js` of htmx.org 4.0.1, from the
#: npm registry, whose own checksums matched it on 2026-11-06. A new version changes this line
#: in the same commit, so a file changed by anything else fails here.
HTMX_SHA256 = "a0abb04f2f45a1f89d1d4844023245537e5e6014c87b144553e0607b4cc32130"


def test_a_page_needs_sign_in_unless_it_is_marked_public(client, settings):
    settings.ROOT_URLCONF = __name__

    response = client.get("/plain/")

    assert response.status_code == 302
    assert response.url.startswith(settings.LOGIN_URL)


def test_every_answer_carries_a_strict_content_security_policy(client, settings):
    settings.ROOT_URLCONF = __name__

    policy = client.get("/plain/")["Content-Security-Policy"]

    assert "script-src 'self'" in policy
    assert "style-src 'self'" in policy
    assert "object-src 'none'" in policy
    assert "unsafe-inline" not in policy
    assert "unsafe-eval" not in policy


def test_english_is_the_only_language_until_a_second_is_wanted(settings):
    assert [code for code, _name in settings.LANGUAGES] == ["en"]
    assert settings.LOCALE_PATHS == [settings.BASE_DIR / "locale"]


def test_business_records_are_never_in_the_admin():
    assert {model._meta.label for model in admin.site._registry} == ADMIN_MODELS.keys()


def test_the_htmx_file_is_the_one_checked(settings):
    htmx = settings.BASE_DIR / "static" / "vendor" / "htmx" / "htmx.min.js"

    assert hashlib.sha256(htmx.read_bytes()).hexdigest() == HTMX_SHA256
