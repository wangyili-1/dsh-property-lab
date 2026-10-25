"""Direct public-API checks; no import of the property adapter or oracle."""

import json
from decimal import Decimal

import humanize


def main() -> None:
    samples = [0, 12345, -12345, 2**53, 2**53 + 1, -(2**53 + 1)]
    rows = []
    for value in samples:
        actual = humanize.intcomma(value, ndigits=0)
        expected = format(Decimal(value), ",.0f")
        rows.append(
            {
                "input": value,
                "actual_ndigits_0": actual,
                "expected_decimal_format": expected,
                "default_ndigits_none": humanize.intcomma(value),
                "decimal_value_preserved": Decimal(actual.replace(",", ""))
                == Decimal(value),
            }
        )
    print(json.dumps({"humanize": humanize.__version__, "observations": rows}, indent=2))


if __name__ == "__main__":
    main()
