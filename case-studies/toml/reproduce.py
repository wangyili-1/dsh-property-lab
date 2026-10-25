"""Inspect the found inputs independently, without the lab or its adapter.

Python 3.11+ supplies tomllib as an independent parser. This diagnostic script
reproduces inputs already discovered by the saved property runs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tomllib

parser = argparse.ArgumentParser()
parser.add_argument("--source", type=Path, help="Optional checked-out upstream root")
args = parser.parse_args()
if args.source:
    sys.path.insert(0, str(args.source.resolve()))

import toml
import toml.decoder
import toml.encoder


def observed(call):
    try:
        return {"value": call(), "error": None}
    except Exception as error:
        return {"value": None, "error": f"{type(error).__name__}: {error}"}


results = []
for name, value in (("control-character", "\x1f"), ("quote-in-list", ['"'])):
    document = {"value": value}
    serialized = observed(lambda: toml.dumps(document))
    row = {"name": name, "input": document, "serialization": serialized}
    if serialized["error"] is None:
        text = serialized["value"]
        row["toml_parse"] = observed(lambda: toml.loads(text))
        row["tomllib_parse"] = observed(lambda: tomllib.loads(text))
    results.append(row)

valid_control_document = 'value = "\\u001f"\n'
output = {
    "python": sys.version.split()[0],
    "toml_version": toml.__version__,
    "source": "upstream-checkout" if args.source else "installed-release",
    "upstream_files": {
        f"toml/{Path(module.__file__).name}": hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in (toml.encoder, toml.decoder)
    },
    "cases": results,
    "valid_control_document": {
        "text": valid_control_document,
        "toml_parse": observed(lambda: toml.loads(valid_control_document)),
        "tomllib_parse": observed(lambda: tomllib.loads(valid_control_document)),
    },
}
print(json.dumps(output, indent=2, ensure_ascii=True))
