# Generated from a recorded property specification. Review the property before adopting it.
# Contract: humanize 4.16.0 documents intcomma as inserting separators into an integer. The independent oracle groups decimal digits without float conversion or numeric formatting. This control uses the identical signed 64-bit input domain as intcomma-zero-digits.json but leaves ndigits at its default None. Official contract: https://humanize.readthedocs.io/en/stable/number/#humanize.number.intcomma .
from hypothesis import given, settings, seed, example, strategies as st
from copy import deepcopy
import importlib
import os
from pathlib import Path
import sys
import tempfile
from uuid import uuid4

# Run from the tested project root, or set PROPERTY_LAB_PROJECT to that directory.
_project = Path(os.environ.get("PROPERTY_LAB_PROJECT", str(Path.cwd())))
for _directory in (_project / "src", _project):
    if _directory.is_dir():
        sys.path.insert(0, str(_directory))

def _load(reference):
    module_name, attribute = reference.split(":", 1)
    old_cache, old_write = sys.pycache_prefix, sys.dont_write_bytecode
    # An unused cache path avoids stale bytecode without creating a directory.
    cache = Path(tempfile.gettempdir()) / ("property-lab-import-" + uuid4().hex)
    try:
        sys.pycache_prefix, sys.dont_write_bytecode = str(cache), True
        value = importlib.import_module(module_name)
    finally:
        sys.pycache_prefix, sys.dont_write_bytecode = old_cache, old_write
    for part in attribute.split("."):
        value = getattr(value, part)
    return value

_function = _load('humanize:intcomma')
_reference = _load('adapter:exact_integer_groups')

def _assert_property(value):
    expected = _reference(deepcopy(value))
    actual = _function(deepcopy(value))
    assert actual == expected, (actual, expected)

@seed(20261025)
@settings(max_examples=3000, deadline=None, database=None)
@given(value=st.integers(min_value=-9223372036854775808, max_value=9223372036854775807))
def test_property(value):
    _assert_property(value)

if __name__ == '__main__':
    test_property()
