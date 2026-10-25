"""Contract-derived adapters for boltons.iterutils.split, with maxsplit fixed at 1."""
from boltons.iterutils import split


def split_once(values):
    return split(values, sep=None, maxsplit=1)


def reference_split_once(values):
    """Injectively encode -9..9 as A..S and None as whitespace.

    The standard library independently implements the documented str.split
    grouping semantics. Spaces later inside the unsplit remainder are decoded
    back to None, so this does not incorrectly remove every later separator.
    """
    encoded = ''.join(' ' if value is None else chr(value + 74) for value in values)
    return [[None if char == ' ' else ord(char) - 74 for char in group]
            for group in encoded.split(None, 1)]
