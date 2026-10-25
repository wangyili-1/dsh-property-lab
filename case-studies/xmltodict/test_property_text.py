# Generated from a recorded property specification. Review the property before adopting it.
# Contract: The documented unparse/parse APIs and upstream test_simple_cdata assert preservation of a simple element text value. This control uses the same legal alphabet as the comment property, and disables whitespace stripping. XML character data must escape markup characters on serialization, then decode them on parsing.
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

_function = _load('xmltodict_adapter:encode_text')
_inverse = _load('xmltodict_adapter:decode_text')

def _assert_property(value):
    expected = deepcopy(value)
    actual = _inverse(_function(deepcopy(value)))
    assert actual == expected, (actual, expected)

@seed(20261025)
@settings(max_examples=3000, deadline=None, database=None)
@given(value=st.text(alphabet='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 &<>;#=\'"[]()_/.:,!?\t\n中文éΩ', min_size=1, max_size=64))
def test_property(value):
    _assert_property(value)

if __name__ == '__main__':
    test_property()
