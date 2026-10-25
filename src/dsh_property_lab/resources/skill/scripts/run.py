"""Bootstrap the pinned Property Lab environment; Python 3.9+ is enough here."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    runtime = Path(__file__).resolve().parents[1] / "runtime.json"
    if not runtime.is_file():
        print("Missing runtime.json. Install with: python -m dsh_property_lab install-dsh", file=sys.stderr)
        return 2
    config = json.loads(runtime.read_text(encoding="utf-8"))
    interpreter = Path(config["python"])
    if not interpreter.is_file():
        print("The pinned Python environment was moved or removed. Re-run install-dsh from the new environment.", file=sys.stderr)
        return 2
    try:
        return subprocess.call([str(interpreter), "-m", "dsh_property_lab", *sys.argv[1:]])
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
