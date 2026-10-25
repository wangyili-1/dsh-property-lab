"""Behavioral integration checks through the public CLI and exported artifacts."""
from __future__ import annotations

import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import sys
import py_compile

import pytest


def invoke(*arguments, cwd=None, timeout=20):
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    # Fixture repairs happen immediately; avoid timestamp-based bytecode reuse.
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, "-m", "dsh_property_lab", *map(str, arguments)],
        cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", timeout=timeout,
    )


def execute_test(path, project):
    env = os.environ.copy()
    env["PROPERTY_LAB_PROJECT"] = str(project)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(path)], cwd=project, env=env,
        capture_output=True, text=True, encoding="utf-8", timeout=20,
    )


@pytest.fixture
def sample(tmp_path):
    project = tmp_path / "project with spaces"
    project.mkdir()
    target = project / "target.py"
    target.write_text(
        "def implementation(value):\n    return value * abs(value)\n\n"
        "def oracle(value):\n    return value ** 2\n", encoding="utf-8",
    )
    spec = {
        "version": 1, "name": "square-contract", "kind": "equivalence",
        "function": "target:implementation", "reference": "target:oracle",
        "strategy": {"type": "integers", "min_value": -10, "max_value": -1},
        "rationale": "The documented result is the square, including negative integers.",
        "domain": "Integers from -10 through -1.",
    }
    spec_path = tmp_path / "property spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    return project, target, spec, spec_path


def write_spec(path, spec):
    path.write_text(json.dumps(spec), encoding="utf-8")


def run_spec(spec_path, project, output, *extra):
    return invoke("run", spec_path, "--project", project, "--output", output,
                  "--max-examples", "30", *extra)


def read_report(output):
    return json.loads((output / "report.json").read_text(encoding="utf-8"))


def test_bug_repair_replay_and_source_fingerprints(sample, tmp_path):
    project, target, _, spec_path = sample
    output = tmp_path / "initial evidence"
    result = run_spec(spec_path, project, output)
    assert result.returncode == 1, result.stdout + result.stderr
    original = read_report(output)
    assert original["status"] == "counterexample"
    assert original["counterexample"] == -1
    assert original["runtime"]["hypothesis"]
    assert original["source_files"][0]["sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    regression = execute_test(output / "test_regression.py", project)
    assert regression.returncode != 0 and "AssertionError" in regression.stderr
    generated = execute_test(output / "test_property.py", project)
    assert generated.returncode != 0 and "AssertionError" in generated.stderr

    target.write_text(
        "def implementation(value):\n    return value * value\n\n"
        "def oracle(value):\n    return value ** 2\n", encoding="utf-8",
    )
    assert execute_test(output / "test_regression.py", project).returncode == 0
    assert execute_test(output / "test_property.py", project).returncode == 0
    replay_output = tmp_path / "repair replay"
    replay = invoke("replay", output / "report.json", "--project", project, "--output", replay_output)
    assert replay.returncode == 0, replay.stdout + replay.stderr
    replay_report = read_report(replay_output)
    assert replay_report["original_source_files"] == original["source_files"]
    assert replay_report["source_files"][0]["sha256"] != original["source_files"][0]["sha256"]
    fresh = run_spec(spec_path, project, tmp_path / "new search")
    assert fresh.returncode == 0, fresh.stdout + fresh.stderr


def test_import_failure_is_error_and_report_explains_it(sample, tmp_path):
    project, target, _, spec_path = sample
    target.write_text("import missing_property_lab_fixture_dependency\n", encoding="utf-8")
    output = tmp_path / "import failure"
    result = run_spec(spec_path, project, output)
    assert result.returncode == 2
    report = read_report(output)
    assert report["status"] == "error" and not report["has_counterexample"]
    assert report["evaluations"] == 0
    assert "missing_property_lab_fixture_dependency" in (output / "report.html").read_text(encoding="utf-8")


def test_repairs_ignore_stale_timestamp_bytecode(sample, tmp_path):
    project, target, spec, spec_path = sample
    buggy = "def implementation(value):\n    return value + 1\n"
    fixed = "def implementation(value):\n    return value + 0\n"
    target.write_text(buggy, encoding="utf-8")
    stamp = target.stat().st_mtime_ns
    py_compile.compile(str(target), doraise=True)
    spec.update(kind="idempotence", rationale="Normalization must be idempotent.")
    del spec["reference"]
    write_spec(spec_path, spec)
    initial = tmp_path / "before repair"
    assert run_spec(spec_path, project, initial).returncode == 1
    target.write_text(fixed, encoding="utf-8")
    os.utime(target, ns=(stamp, stamp))
    # Equal size and mtime would make Python accept the stale compiled bug.
    assert len(buggy) == len(fixed)
    assert run_spec(spec_path, project, tmp_path / "after repair").returncode == 0
    assert execute_test(initial / "test_regression.py", project).returncode == 0
    assert execute_test(initial / "test_property.py", project).returncode == 0


def test_hanging_target_is_inconclusive(sample, tmp_path):
    project, target, _, spec_path = sample
    target.write_text(
        "import time\ndef implementation(value):\n    while True:\n        time.sleep(1)\n"
        "def oracle(value):\n    return value * value\n", encoding="utf-8",
    )
    output = tmp_path / "timeout evidence"
    result = run_spec(spec_path, project, output, "--timeout", "1")
    assert result.returncode == 2, result.stdout + result.stderr
    report = read_report(output)
    assert report["status"] == "inconclusive"
    assert not report["has_counterexample"]
    assert "timeout" in report["error"].lower()


def test_output_directory_is_not_overwritten(sample, tmp_path):
    project, _, _, spec_path = sample
    output = tmp_path / "existing output"
    output.mkdir()
    sentinel = output / "my evidence.txt"
    sentinel.write_text("do not replace", encoding="utf-8")
    result = run_spec(spec_path, project, output)
    assert result.returncode == 2
    assert "not empty" in result.stderr
    assert sentinel.read_text(encoding="utf-8") == "do not replace"
    assert sorted(path.name for path in output.iterdir()) == ["my evidence.txt"]


def test_report_escapes_target_text(sample, tmp_path):
    project, _, spec, spec_path = sample
    injection = '<script>alert("contract")</script> & <img src=x onerror=alert(1)>'
    spec["rationale"] = injection
    spec["domain"] = injection
    write_spec(spec_path, spec)
    output = tmp_path / "escaped report"
    result = run_spec(spec_path, project, output)
    assert result.returncode == 1
    document = (output / "report.html").read_text(encoding="utf-8")
    assert injection not in document
    assert html.escape(injection) in document


def test_none_counterexample_survives_cli_replay_and_export(sample, tmp_path):
    project, target, spec, spec_path = sample
    target.write_text(
        "def implementation(value):\n    return 0\n\n"
        "def oracle(value):\n    return value\n", encoding="utf-8",
    )
    spec["strategy"] = {"type": "just", "value": None}
    spec["domain"] = "The singleton input None."
    write_spec(spec_path, spec)
    output = tmp_path / "null evidence"
    result = run_spec(spec_path, project, output)
    assert result.returncode == 1
    report = read_report(output)
    assert report["has_counterexample"] and report["counterexample"] is None
    assert "COUNTEREXAMPLE = None" in (output / "test_regression.py").read_text(encoding="utf-8")
    regression = execute_test(output / "test_regression.py", project)
    assert regression.returncode != 0 and "AssertionError" in regression.stderr
    replay = invoke("replay", output / "report.json", "--output", tmp_path / "null replay")
    assert replay.returncode == 1


def test_mutating_list_target_gets_independent_oracle_input(sample, tmp_path):
    project, target, spec, spec_path = sample
    target.write_text(
        "def implementation(value):\n    value.append(0)\n    return value\n\n"
        "def oracle(value):\n    return value + [0]\n", encoding="utf-8",
    )
    spec["strategy"] = {"type": "lists", "elements": {"type": "integers"}, "max_size": 5}
    spec["domain"] = "Lists of integers with at most five elements."
    write_spec(spec_path, spec)
    output = tmp_path / "mutable inputs"
    result = run_spec(spec_path, project, output)
    assert result.returncode == 0, result.stdout + result.stderr
    exported = execute_test(output / "test_property.py", project)
    assert exported.returncode == 0, exported.stdout + exported.stderr


def test_src_layout_export_reproduces_assertion(sample, tmp_path):
    project, target, _, spec_path = sample
    source = project / "src"
    source.mkdir()
    target.rename(source / target.name)
    output = tmp_path / "src layout evidence"
    result = run_spec(spec_path, project, output)
    assert result.returncode == 1, result.stdout + result.stderr
    exported = execute_test(output / "test_regression.py", project)
    assert exported.returncode != 0
    assert "AssertionError" in exported.stderr, exported.stdout + exported.stderr
    assert "ModuleNotFoundError" not in exported.stderr
