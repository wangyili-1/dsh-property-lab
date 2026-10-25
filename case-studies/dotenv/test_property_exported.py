# Generated from a recorded property specification. Review the property before adopting it.
# Contract: python-dotenv v1.2.4 README File format documents quoted values, escaped backslashes and quotes, and multiline values; tests/test_main.py::test_set_key_round_trips asserts writing and reading restores strings and preserves a following sentinel. src/dotenv/main.py documents interpolate=False to disable POSIX expansion. This extends that existing contract to combinations of the stated characters, using the real public set_key and dotenv_values APIs.
from hypothesis import given, settings, seed, example, strategies as st
from copy import deepcopy
import importlib
import os
from pathlib import Path
import sys
import tempfile

# Run from the tested project root, or set PROPERTY_LAB_PROJECT to that directory.
_project = Path(os.environ.get("PROPERTY_LAB_PROJECT", str(Path.cwd())))
for _directory in (_project / "src", _project):
    if _directory.is_dir():
        sys.path.insert(0, str(_directory))

def _load(reference):
    module_name, attribute = reference.split(":", 1)
    old_cache, old_write = sys.pycache_prefix, sys.dont_write_bytecode
    with tempfile.TemporaryDirectory(prefix="property-lab-import-") as cache:
        try:
            sys.pycache_prefix, sys.dont_write_bytecode = cache, True
            value = importlib.import_module(module_name)
        finally:
            sys.pycache_prefix, sys.dont_write_bytecode = old_cache, old_write
    for part in attribute.split("."):
        value = getattr(value, part)
    return value

_function = _load('adapter:write_value')
_inverse = _load('adapter:read_value')

def _assert_property(value):
    expected = deepcopy(value)
    actual = _inverse(_function(deepcopy(value)))
    assert actual == expected, (actual, expected)

@seed(20261025)
@settings(max_examples=2500, deadline=None, database=None)
@given(value=st.text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 _-./\\\'"#=$:{}+%\n\té中🙂', min_size=0, max_size=120))
def test_property(value):
    _assert_property(value)

if __name__ == '__main__':
    test_property()
