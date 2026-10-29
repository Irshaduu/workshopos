"""The module list: each app adds its own modules (ADR-0011, ADR-0026)."""

import pytest

from apps.workshops.modules import MODULES, Module, add_modules


def test_each_app_adds_its_own_modules_at_start():
    # accounts adds its modules from its ready(); this lower app imports none.
    assert {"sign_in", "roles"} <= set(MODULES)


def test_two_different_modules_never_share_a_key(monkeypatch):
    monkeypatch.setattr("apps.workshops.modules.MODULES", {})
    add_modules(Module("cashbook", "Cashbook"))

    # Adding the same module again changes nothing, as when Django calls
    # ready() twice.
    add_modules(Module("cashbook", "Cashbook"))

    with pytest.raises(ValueError, match="cashbook"):
        add_modules(Module("cashbook", "Cash book", core=True))
