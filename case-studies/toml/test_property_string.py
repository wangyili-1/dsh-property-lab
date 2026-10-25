# Generated from a recorded property specification. Review the property before adopting it.
# Contract: toml documents dumps as producing TOML corresponding to a Python dictionary and loads as parsing that TOML into a dictionary. TOML 0.5.0 permits valid Unicode scalar values in basic strings, with control characters escaped. Upstream tests/test_api.py includes roundtrip assertions. The adapter only wraps the generated string in a fixed-key dictionary and unwraps it after parsing.
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

_function = _load('toml_adapter:encode_value')
_inverse = _load('toml_adapter:decode_value')

def _assert_property(value):
    expected = deepcopy(value)
    actual = _inverse(_function(deepcopy(value)))
    assert actual == expected, (actual, expected)

@example(value='\x1f')
@seed(20261025)
@settings(max_examples=2000, deadline=None, database=None)
@given(value=st.text(min_size=0, max_size=64))
def test_property(value):
    _assert_property(value)

if __name__ == '__main__':
    test_property()
