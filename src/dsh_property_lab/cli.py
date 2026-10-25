"""Command line interface. No model API or DSH credentials are used here."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from . import __version__
from .artifacts import dump_json, write_demo_index, write_report, write_tests
from .integration import doctor, install_dsh, example_directory
from .spec import SpecError, load_spec, validate_spec


def positive_int(value: str) -> int:
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return result


def output_directory(value: str | Path | None, project: Path, name: str) -> Path:
    if value:
        path = Path(value).resolve()
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = project / ".property-lab" / "runs" / f"{stamp}-{name}-{uuid.uuid4().hex[:6]}"
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError(f"Output directory is not empty: {path}. Choose a new directory to preserve earlier evidence.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def stop_worker(process: subprocess.Popen) -> None:
    """Stop only the process tree launched for this run."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW, check=False)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def execute(spec: dict, project: Path, output: Path, *, seed: int, max_examples: int,
            timeout: int, replay: dict | None = None) -> dict:
    started = datetime.now(timezone.utc).isoformat()
    request = {"mode": "replay" if replay is not None else "run", "spec": spec,
               "project": str(project), "seed": seed, "max_examples": max_examples}
    if replay is not None:
        request["counterexample"] = replay["counterexample"]
    dump_json(output / "spec.json", spec)
    dump_json(output / "request.json", request)
    response = output / "worker.json"
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
    worker_env = os.environ.copy()
    # Read current source even when a repair keeps the same file size/mtime.
    # A fresh cache prefix plus no bytecode writes also leaves the target clean.
    worker_env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
                      PYTHONPYCACHEPREFIX=str(output / ".bytecode-cache"))
    started_clock = time.monotonic()
    with (output / "process.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen([sys.executable, "-m", "dsh_property_lab._worker",
                                    str(output / "request.json"), str(response)],
                                   cwd=project, env=worker_env, stdin=subprocess.DEVNULL, stdout=log, stderr=log, **options)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            stop_worker(process)
            result = {"status": "inconclusive", "has_counterexample": False, "evaluations": None,
                      "error": f"Worker exceeded the {timeout}s wall-clock timeout. No reliable result was returned."}
        except KeyboardInterrupt:
            stop_worker(process)
            raise
        else:
            if code == 0 and response.is_file():
                try:
                    result = json.loads(response.read_text(encoding="utf-8"))
                    if not isinstance(result, dict) or result.get("status") not in {"counterexample", "no_counterexample", "inconclusive", "error"}:
                        raise ValueError("Invalid worker response")
                except (ValueError, OSError) as exc:
                    result = {"status": "error", "has_counterexample": False, "error": str(exc)}
            else:
                result = {"status": "error", "has_counterexample": False,
                          "error": f"Worker exited with code {code}; see process.log and worker.log."}
    result.setdefault("duration_seconds", round(time.monotonic() - started_clock, 4))
    result.update({"schema_version": 1, "spec": spec, "project": str(project), "output": str(output),
                   "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
                   "seed": seed, "max_examples": max_examples, "timeout_seconds": timeout,
                   "spec_sha256": hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()})
    if replay is not None:
        result["replayed_from"] = replay.get("output")
        result["original_source_files"] = replay.get("source_files", [])
    (output / "worker.log").touch(exist_ok=True)
    write_tests(result, output)
    write_report(result, output)
    return result


def print_result(report: dict) -> int:
    print(f"Status: {report['status']}")
    if report.get("has_counterexample"):
        print("Counterexample: " + json.dumps(report["counterexample"], ensure_ascii=True))
        print("Review the property and input domain before classifying an implementation defect.")
    else:
        print(report.get("error") or report.get("message") or "No violating input found; this is not a proof.")
    print(f"Report: {Path(report['output']) / 'report.html'}")
    print(f"Evidence: {Path(report['output']) / 'report.json'}")
    return {"no_counterexample": 0, "counterexample": 1}.get(report["status"], 2)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="dsh-property-lab", description="Run, shrink and replay Python properties with Hypothesis.")
    result.add_argument("--version", action="version", version=__version__)
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect interpreter, dependencies and local DSH skill installation")
    install = commands.add_parser("install-dsh", help="Install the user-level DSH skill without modifying profiles")
    install.add_argument("--dsh-home", type=Path)
    run = commands.add_parser("run", help="Execute a JSON property specification in a fresh worker")
    run.add_argument("spec", type=Path)
    replay = commands.add_parser("replay", help="Replay an exact counterexample saved in report.json")
    replay.add_argument("report", type=Path)
    for command in (run, replay):
        command.add_argument("--project", type=Path, help="Target project root; replay defaults to the original project")
        command.add_argument("--output", type=Path, help="New or empty evidence directory")
        command.add_argument("--timeout", type=positive_int, default=60)
    run.add_argument("--seed", type=int, default=2026)
    run.add_argument("--max-examples", type=positive_int, default=300)
    demo = commands.add_parser("demo", help="Verify three deliberately buggy/fixed fixture pairs")
    demo.add_argument("--output", type=Path)
    demo.add_argument("--timeout", type=positive_int, default=60)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(doctor(), ensure_ascii=True, indent=2))
            return 0
        if args.command == "install-dsh":
            installed = install_dsh(args.dsh_home)
            print(f"Installed DSH skill: {installed}")
            print("Open a new DSH conversation and use /dsh-property-lab.")
            return 0
        if args.command == "demo":
            examples = example_directory()
            project = examples.parent
            output = output_directory(args.output, Path.cwd(), "demo")
            rows = []
            for kind in ("roundtrip", "idempotence", "equivalence"):
                for variant in ("buggy", "fixed"):
                    filename = f"{kind}-{variant}"
                    spec = load_spec(examples / f"{filename}.json")
                    run_output = output_directory(output / filename, project, spec["name"])
                    report = execute(spec, project, run_output, seed=2026, max_examples=300, timeout=args.timeout)
                    expected = "counterexample" if variant == "buggy" else "no_counterexample"
                    rows.append({"name": spec["name"], "directory": filename, "expected": expected,
                                 "status": report["status"], "matched": report["status"] == expected})
                    print(f"{filename}: {report['status']} (expected {expected})")
            write_demo_index(rows, output)
            print(f"Demo: {output / 'index.html'}")
            return 0 if all(row["matched"] for row in rows) else 2
        original = None
        if args.command == "replay":
            original = json.loads(args.report.read_text(encoding="utf-8"))
            if not original.get("has_counterexample") or "counterexample" not in original:
                raise ValueError("This report contains no confirmed counterexample to replay.")
            spec = validate_spec(original["spec"])
            project = (args.project or Path(original["project"])).resolve()
            seed, max_examples = original.get("seed", 2026), original.get("max_examples", 300)
        else:
            spec = load_spec(args.spec)
            project = (args.project or Path.cwd()).resolve()
            seed, max_examples = args.seed, args.max_examples
        if not project.is_dir():
            raise ValueError(f"Project directory does not exist: {project}")
        output = output_directory(args.output, project, ("replay-" if original else "") + spec["name"])
        return print_result(execute(spec, project, output, seed=seed, max_examples=max_examples,
                                    timeout=args.timeout, replay=original))
    except (SpecError, ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted; the worker was stopped.", file=sys.stderr)
        return 130
