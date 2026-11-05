"""Tidying what a person typed, for every app that keeps a name."""


def tidy_spaces(typed):
    """Spaces at the ends and double spaces go, so a second copy cannot hide behind them."""
    return " ".join(typed.split())


def tidy_name(typed):
    """A name as it is saved (STAFF-6).

    A name typed with no capitals gets one at the start of each word. A name typed with
    its own capitals keeps them, and only its first letter is raised, so "anil KP" is
    "Anil KP" and "Mohammed bin Salim" stays. No capital is ever made small, so whatever
    is typed can be kept.
    """
    name = tidy_spaces(typed)
    return name.title() if name.islower() else name[:1].upper() + name[1:]
