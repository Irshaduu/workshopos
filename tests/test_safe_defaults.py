"""Safe defaults from the first app: sign-in, a strict CSP, and one language."""

from django.http import HttpResponse
from django.urls import path


def plain_page(request):
    return HttpResponse("A page nobody marked public.")


urlpatterns = [path("plain/", plain_page)]


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
