#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
"${PYTHON:-python3}" -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/python" -m pip install -e "$ROOT[dev]"
"$ROOT/.venv/bin/python" -m dsh_property_lab doctor
printf '%s\n' "Ready: $ROOT/.venv/bin/python -m dsh_property_lab demo"
