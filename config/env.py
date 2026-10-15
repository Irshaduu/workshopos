"""Read settings from environment variables, with an optional local .env file.

The .env file is for a developer's own machine and is never committed;
.env.example lists every variable. A value already set in the environment
always wins over the file.
"""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def load_env_file(path: Path) -> None:
    """Copy NAME=value lines from the file into the environment, unless already set."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip())


def env(name: str, default: str | None = None) -> str:
    """Return an environment variable.

    With no default, a missing or empty value stops the start-up.
    """
    value = os.environ.get(name, "")
    if value:
        return value
    if default is None:
        raise ImproperlyConfigured(f"Set {name} in the environment or in .env (see .env.example).")
    return default
