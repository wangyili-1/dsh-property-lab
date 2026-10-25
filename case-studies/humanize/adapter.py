"""Thin calls to humanize and an exact, independently grouped integer oracle."""

import humanize


def intcomma_zero_digits(value: int) -> str:
    """Request zero fractional digits for an already exact integer."""
    return humanize.intcomma(value, ndigits=0)


def exact_integer_groups(value: int) -> str:
    """Group the decimal digits without floats or numeric format specifiers."""
    sign = "-" if value < 0 else ""
    digits = str(abs(value))
    groups = []
    while digits:
        groups.append(digits[-3:])
        digits = digits[:-3]
    return sign + ",".join(reversed(groups))
