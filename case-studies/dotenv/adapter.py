"""Thin python-dotenv adapter; all files are synthetic and auto-cleaned."""

from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import dotenv_values, set_key


def write_value(value: str) -> str:
    """Serialize VALUE and a following sentinel through the public set_key API."""
    # Stay inside this case directory; never search for or load a user's .env.
    with TemporaryDirectory(prefix=".dotenv-case-", dir=Path(__file__).parent) as tmp:
        path = Path(tmp) / "synthetic.env"
        set_key(path, "VALUE", value, quote_mode="always", encoding="utf-8")
        set_key(path, "SENTINEL", "unchanged", quote_mode="always", encoding="utf-8")
        # Standard text mode normalizes platform line endings to LF. The input
        # alphabet excludes CR; the public file reader uses the same behavior.
        return path.read_text(encoding="utf-8")


def read_value(serialized: str) -> str:
    """Read literal strings without POSIX expansion or modifying os.environ."""
    values = dotenv_values(stream=StringIO(serialized), interpolate=False)
    assert set(values) == {"VALUE", "SENTINEL"}, values
    assert values["SENTINEL"] == "unchanged", values
    return values["VALUE"]
