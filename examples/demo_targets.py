"""Small, deliberately faulty examples with explicit contracts.

These are teaching fixtures, not bugs discovered in a third-party project.
Every target takes one positional argument and returns a JSON-compatible value.
"""

import re
from urllib.parse import quote_plus, unquote_plus


def encode_buggy(text: str) -> str:
    """Form-encode text, incorrectly treating literal '+' as a safe character."""
    return quote_plus(text, safe="+")


def encode_fixed(text: str) -> str:
    """Form-encode text so decoding restores every original character."""
    return quote_plus(text, safe="")


def decode(text: str) -> str:
    """Decode form-encoded text; a bare '+' denotes a space."""
    return unquote_plus(text)


def normalize_buggy(text: str) -> str:
    """Collapse ASCII space runs, incorrectly making only one replacement pass."""
    return text.replace("  ", " ")


def normalize_fixed(text: str) -> str:
    """Collapse each run of ASCII spaces to one, preserving boundary spaces."""
    return re.sub(r" +", " ", text)


def unique_buggy(values: list[int]) -> list[int]:
    """Remove duplicates, incorrectly sorting instead of preserving first occurrence."""
    return sorted(set(values))


def unique_fixed(values: list[int]) -> list[int]:
    """Remove duplicates while preserving the order of first occurrence."""
    return list(dict.fromkeys(values))


def reference_unique(values: list[int]) -> list[int]:
    """Simple independent reference for the stable-unique contract."""
    result: list[int] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result
