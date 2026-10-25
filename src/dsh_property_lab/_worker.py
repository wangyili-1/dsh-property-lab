"""Private worker protocol. User code is executed here, never in the CLI process."""
from __future__ import annotations

import contextlib
import hashlib
import json
import platform
import sys
import time
import traceback
from pathlib import Path

import hypothesis

from . import __version__
from .engine import evaluate_example, run_property
from .spec import validate_spec


def fingerprints(spec: dict) -> list[dict]:
    found = {}
    for key in ("function", "inverse", "reference"):
        if key not in spec:
            continue
        module_name = spec[key].split(":", 1)[0]
        module = sys.modules.get(module_name)
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).is_file():
            path = Path(filename).resolve()
            found[str(path)] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return list(found.values())


def main() -> int:
    request_path, response_path = map(Path, sys.argv[1:3])
    started = time.monotonic()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    result = {}
    with response_path.with_suffix(".log").open("w", encoding="utf-8") as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            try:
                spec = validate_spec(request["spec"])
                project = Path(request["project"])
                if request["mode"] == "replay":
                    observation = evaluate_example(spec, project, request["counterexample"])
                    result = {
                        "status": "no_counterexample" if observation["passed"] else "counterexample",
                        "has_counterexample": not observation["passed"],
                        "counterexample": request["counterexample"],
                        "observation": observation,
                        "evaluations": 1,
                        "replay": True,
                    }
                else:
                    result = run_property(spec, project, seed=request["seed"], max_examples=request["max_examples"])
                result["source_files"] = fingerprints(spec)
            except Exception as exc:
                traceback.print_exc()
                result = {"status": "error", "has_counterexample": False,
                          "error": f"{type(exc).__name__}: {exc}", "evaluations": 0}
    result["duration_seconds"] = round(time.monotonic() - started, 4)
    result["runtime"] = {"python": platform.python_version(), "executable": sys.executable,
                         "hypothesis": hypothesis.__version__, "property_lab": __version__,
                         "platform": platform.platform()}
    response_path.write_text(json.dumps(result, ensure_ascii=True, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
