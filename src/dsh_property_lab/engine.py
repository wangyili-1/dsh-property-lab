"""Execute one unary property in a worker process managed by the CLI.

This module imports and runs the selected local project. It is not a sandbox;
the caller supplies process isolation and a wall-clock timeout.
"""

from __future__ import annotations

import copy
import importlib
import inspect
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

import hypothesis
from hypothesis import Phase, find, settings
from hypothesis.errors import Flaky, NoSuchExample, Unsatisfiable

from .spec import SpecError, build_strategy, validate_spec


def _render(value: Any) -> str:
    try:
        result = repr(value)
    except Exception as exc:
        result = f"<repr failed: {type(exc).__name__}>"
    return result if len(result) <= 4000 else result[:4000] + " ... [truncated]"


def _resolve(reference: str) -> Callable:
    module_name, attribute = reference.split(":", 1)
    target = importlib.import_module(module_name)
    for part in attribute.split("."):
        target = getattr(target, part)
    if not callable(target):
        raise SpecError(f"{reference} is not callable")
    if inspect.iscoroutinefunction(target) or inspect.isasyncgenfunction(target):
        raise SpecError(f"{reference}: async functions are not supported in version 1")
    try:
        signature = inspect.signature(target)
    except (ValueError, TypeError):
        pass  # A few extension functions do not expose inspectable signatures.
    else:
        try:
            signature.bind(object())
        except TypeError as exc:
            raise SpecError(f"{reference}: expected a function callable with one positional argument: {exc}") from exc
    return target


def _prepare(spec: dict, project_root: str | Path) -> tuple[dict, dict[str, Callable]]:
    spec = validate_spec(spec)
    root = Path(project_root).resolve()
    if not root.is_dir():
        raise SpecError(f"Project directory does not exist: {root}")
    # Support both conventional and src-layout projects. The CLI launches a
    # fresh interpreter per run, so modules from different projects cannot mix.
    for directory in (root / "src", root):
        if directory.is_dir() and str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
    importlib.invalidate_caches()
    targets = {"function": _resolve(spec["function"])}
    for role in ("inverse", "reference"):
        if role in spec:
            targets[role] = _resolve(spec[role])
    if spec["kind"] == "equivalence" and targets["function"] is targets["reference"]:
        raise SpecError("function and reference resolve to the same callable; use an independent oracle")
    return spec, targets


def _evaluate(spec: dict, targets: dict[str, Callable], value: Any) -> dict:
    actual: Any = "<not evaluated>"
    expected: Any = copy.deepcopy(value) if spec["kind"] == "roundtrip" else "<not evaluated>"
    try:
        if spec["kind"] == "roundtrip":
            actual = targets["inverse"](targets["function"](copy.deepcopy(value)))
        elif spec["kind"] == "idempotence":
            first = targets["function"](copy.deepcopy(value))
            expected = copy.deepcopy(first)
            actual = targets["function"](copy.deepcopy(first))
        else:
            expected = targets["reference"](copy.deepcopy(value))
            actual = targets["function"](copy.deepcopy(value))
        passed = bool(actual == expected)
        return {"passed": passed, "actual": _render(actual), "expected": _render(expected), "error": None}
    except Exception as exc:
        return {
            "passed": False,
            "actual": _render(actual),
            "expected": _render(expected),
            "error": f"{type(exc).__name__}: {exc}"[:4000],
        }


def evaluate_example(spec: dict, project_root: str | Path, value: Any) -> dict:
    """Replay an exact input; setup errors raise instead of masquerading as bugs."""
    spec, targets = _prepare(spec, project_root)
    return _evaluate(spec, targets, value)


def run_property(
    spec: dict,
    project_root: str | Path,
    *,
    seed: int = 2026,
    max_examples: int = 500,
) -> dict:
    """Search and shrink a violating input, then replay it three times.

    ``evaluations`` counts predicate calls, including shrinking. The configured
    ``max_examples`` is Hypothesis' search budget, not a promise of that many
    distinct examples. An exhausted search does not establish correctness.
    """
    start = time.monotonic()
    result = {
        "status": "error",
        "has_counterexample": False,
        "counterexample": None,
        "evaluations": 0,
        "observation": None,
        "seed": seed,
        "max_examples": max_examples,
        "hypothesis_version": hypothesis.__version__,
    }
    try:
        if type(seed) is not int:
            raise SpecError("seed: expected an integer")
        if type(max_examples) is not int or max_examples < 1:
            raise SpecError("max_examples: expected an integer >= 1")
        spec, targets = _prepare(spec, project_root)
        strategy = build_strategy(spec["strategy"])

        def violates(value: Any) -> bool:
            result["evaluations"] += 1
            observation = _evaluate(spec, targets, value)
            return not observation["passed"]

        try:
            value = find(
                strategy,
                violates,
                settings=settings(
                    max_examples=max_examples,
                    database=None,
                    deadline=None,
                    phases=(Phase.generate, Phase.shrink),
                ),
                random=random.Random(seed),
            )
        except NoSuchExample:
            result.update(
                status="no_counterexample",
                message="No counterexample found within this search budget; this is not proof of correctness.",
            )
        else:
            # Fresh copies prevent an in-place function from changing the input
            # stored in evidence, the oracle's input, or subsequent replays.
            observations = [_evaluate(spec, targets, copy.deepcopy(value)) for _ in range(3)]
            result.update(
                counterexample=copy.deepcopy(value),
                observation=observations[0],
                replay_observations=observations,
                replay_count=3,
            )
            if any(observation["passed"] for observation in observations) or any(
                observation != observations[0] for observation in observations[1:]
            ):
                result.update(
                    status="inconclusive",
                    message="The candidate did not reproduce consistently. Inspect state, randomness and the property before treating it as a bug.",
                )
            else:
                result.update(
                    status="counterexample",
                    has_counterexample=True,
                    message="A Hypothesis-shrunk counterexample reproduced three times. Review whether the property and input domain are valid before classifying a code defect.",
                    classification="needs_review",
                )
    except (Flaky, Unsatisfiable) as exc:
        result.update(status="inconclusive", message=f"{type(exc).__name__}: {exc}"[:4000])
    except Exception as exc:
        result.update(status="error", message=f"{type(exc).__name__}: {exc}"[:4000])
    result["elapsed_seconds"] = round(time.monotonic() - start, 6)
    return result
