"""For a bad day for email: a sign-in code the developer gives an owner by phone (SIGN-28).

Run on the server, after the owner has typed their email on the sign-in page:

    uv run python manage.py sign_in_code owner@example.com
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.services import remake_sign_in_code


class Command(BaseCommand):
    help = (
        "Makes a sign-in code for an owner whose browser is on the code step, "
        "to give to them by phone (SIGN-28)."
    )

    def add_arguments(self, parser):
        parser.add_argument("email", help="The owner's email, as typed on the sign-in page.")

    def handle(self, *args, email, **options):
        made = remake_sign_in_code(email)
        if made is None:
            raise CommandError(
                "This owner has no open code. Ask them to type their email on the "
                "sign-in page first, then run this again."
            )
        code, record = made
        asked = timezone.localtime(record.created_at)
        ends = timezone.localtime(record.ends_at)
        # The time it was asked for, so you can check it is the owner's browser.
        self.stdout.write(
            f"Code {code}, for the browser that asked at {asked:%H:%M}. "
            f"It works until {ends:%H:%M}.\n"
            "Give it to the owner by phone, never by email or chat."
        )
