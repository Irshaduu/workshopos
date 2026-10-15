"""Settings for the test run."""

from .base import *  # noqa: F403

# A fast password hasher: tests create many users, and the real one is slow on purpose.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
