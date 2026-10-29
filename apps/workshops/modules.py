"""The module list: every part of the system a page can belong to (ADR-0011).

Each app adds its own modules from its AppConfig.ready(), so this lower app
never imports an upper one (ADR-0005). For now the list only names the
modules; the switch per workshop comes when a workshop first needs a module
off (ADR-0011).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    """One module of docs/MODULES.md."""

    key: str
    name: str
    #: A core module can never be turned off (ADR-0011).
    core: bool = False
    #: The keys of the modules it needs: turning it on turns them on too.
    needs: tuple[str, ...] = ()


#: Every module, by its key.
MODULES: dict[str, Module] = {}


def add_modules(*modules):
    """Adds an app's modules to the list. Two different modules never share a key."""
    for module in modules:
        if MODULES.get(module.key, module) != module:
            raise ValueError(f"Two modules have the key {module.key!r}.")
        MODULES[module.key] = module
