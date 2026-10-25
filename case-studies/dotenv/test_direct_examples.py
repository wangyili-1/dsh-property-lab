"""Explicit edge controls through the public file-reading API, without adapter."""

import pytest
from dotenv import dotenv_values, set_key
from fixture_directory import fixture_directory


@pytest.mark.parametrize(
    "value",
    [
        "",
        "plain",
        "it's",
        'say "hi"',
        "C:\\Users\\",
        "\\d+",
        "a\\'b",
        "a\\nb",
        "line one\nline two",
        "\n",
        "\t",
        " ${VALUE} ",
        "${MISSING:-default}",
        "# = é中🙂",
    ],
)
def test_direct_file_roundtrip(value):
    with fixture_directory(prefix=".dotenv-control-") as tmp:
        path = tmp / "synthetic.env"
        set_key(path, "VALUE", value, quote_mode="always", encoding="utf-8")
        set_key(path, "SENTINEL", "unchanged", quote_mode="always", encoding="utf-8")
        assert dotenv_values(path, interpolate=False, encoding="utf-8") == {
            "VALUE": value,
            "SENTINEL": "unchanged",
        }
