# Generated from a recorded property specification. Review the property before adopting it.
# Contract: boltons 26.2.0 split says it behaves like str.split for iterables; split_iter explicitly says sep=None groups consecutive separators. With maxsplit fixed at positive 1, compare against str.split(None, 1) through an injective encoding of integer tokens as ASCII letters and None as space. The entire first separating run must be consumed. Separators later inside the unsplit remainder remain there; the oracle does not require all separators to disappear. Source: https://github.com/mahmoud/boltons/blob/4332b35a278d694f30c99881faa61cde695c7a96/boltons/iterutils.py#L109-L198 . This is a documented-behavior check, not a claim of maintainer-confirmed novelty.
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

_function = _load('boltons_boundaries_adapter:split_once')
_reference = _load('boltons_boundaries_adapter:reference_split_once')

def _assert_property(value):
    expected = _reference(deepcopy(value))
    actual = _function(deepcopy(value))
    assert actual == expected, (actual, expected)

COUNTEREXAMPLE = [0, None, None]

def test_regression():
    _assert_property(COUNTEREXAMPLE)

if __name__ == '__main__':
    test_regression()
