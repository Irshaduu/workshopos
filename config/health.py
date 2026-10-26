"""The health check: hosts and uptime monitors call it to see if the site works (ADR-0014)."""

import logging

from django.contrib.auth.decorators import login_not_required
from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

logger = logging.getLogger(__name__)


# Public: the host and the uptime monitor call it without signing in.
@login_not_required
@never_cache
@require_safe
def health(request):
    """Answer 200 when the database answers, 503 when it does not."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.exception("Health check: the database did not answer.")
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ok"})
