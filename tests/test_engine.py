from __future__ import annotations

import copy
import json
import uuid

import pytest
from hypothesis import strategies as st

from dsh_property_lab.engine import evaluate_example, run_property
from dsh_property_lab.spec import SpecError, build_strategy, load_spec, strategy_source, validate_spec


@pytest.fixture
def functions(tmp_path):
    module = "fixture_" + uuid.uuid4().hex
    (tmp_path / f"{module}.py").write_text(
        '''
import json

def encode_bad(x): return json.dumps(x).replace("-", "")
def encode_good(x): return json.dumps(x)
def decode(x): return json.loads(x)
def normalize_bad(x): return x.replace("  ", " ", 1)
def normalize_good(x): return " ".join(x.split())
def square_bad(x): return x * abs(x)
def square_good(x): return x * x
def square_oracle(x): return pow(x, 2)
def mutate(x):
    x.append(0)
    return x
def append_oracle(x): return x + [0]
def identity(x): return x
def explode(x): raise RuntimeError("domain or implementation needs review")
def two_args(x, y): return x + y
calls = 0
def unstable(x):
    global calls
    calls += 1
    return x + calls
''', encoding="utf-8"
    )
    return tmp_path, module


def make_spec(module, kind="equivalence", function="square_bad", **extras):
    spec = {
        "version": 1, "name": "example", "kind": kind,
        "function": f"{module}:{function}",
        "strategy": {"type": "integers", "min_value": -100, "max_value": 100},
        "rationale": "Compare with an independently expressed square oracle.",
        "domain": "Integers from -100 to 100, including negative values.",
    }
    if kind == "equivalence":
        spec["reference"] = f"{module}:square_oracle"
    elif kind == "roundtrip":
        spec["inverse"] = f"{module}:decode"
    spec.update(extras)
    return spec


@pytest.mark.parametrize("kind,bad,good,strategy", [
    ("roundtrip", "encode_bad", "encode_good", {"type": "integers", "min_value": -50, "max_value": 50}),
    ("idempotence", "normalize_bad", "normalize_good", {"type": "text", "alphabet": " ab", "max_size": 20}),
    ("equivalence", "square_bad", "square_good", {"type": "integers", "min_value": -50, "max_value": 50}),
])
def test_defect_shrinks_and_repair_passes(functions, kind, bad, good, strategy):
    root, module = functions
    spec = make_spec(module, kind, bad, strategy=strategy)
    result = run_property(spec, root, max_examples=300, seed=17)
    assert result["status"] == "counterexample", result
    assert result["has_counterexample"]
    assert not evaluate_example(spec, root, result["counterexample"])["passed"]
    assert result["replay_count"] == 3
    if kind in ("roundtrip", "equivalence"):
        assert result["counterexample"] == -1
    spec["function"] = f"{module}:{good}"
    assert evaluate_example(spec, root, result["counterexample"])["passed"]
    assert run_property(spec, root, max_examples=100)["status"] == "no_counterexample"


def test_mutation_does_not_pollute_oracle_or_original(functions):
    root, module = functions
    spec = make_spec(module, function="mutate", reference=f"{module}:append_oracle", strategy={"type": "lists", "elements": {"type": "integers"}, "max_size": 5})
    value = [1, 2]
    assert evaluate_example(spec, root, value)["passed"]
    assert value == [1, 2]
    assert run_property(spec, root, max_examples=50)["status"] == "no_counterexample"


def test_exception_is_reviewable_counterexample(functions):
    root, module = functions
    spec = make_spec(module, function="explode")
    result = run_property(spec, root, max_examples=20)
    assert result["status"] == "counterexample"
    assert "RuntimeError" in result["observation"]["error"]
    assert result["classification"] == "needs_review"


def test_nonreproducible_output_is_inconclusive(functions):
    root, module = functions
    spec = make_spec(module, function="unstable", reference=f"{module}:identity", strategy={"type": "just", "value": 0})
    result = run_property(spec, root, max_examples=10)
    assert result["status"] == "inconclusive", result
    assert not result["has_counterexample"]


def test_null_is_a_real_counterexample(functions):
    root, module = functions
    spec = make_spec(module, function="explode", strategy={"type": "just", "value": None})
    result = run_property(spec, root, max_examples=5)
    assert result["has_counterexample"] and result["counterexample"] is None


def test_setup_error_is_not_a_counterexample(functions):
    root, module = functions
    for target in (f"{module}:missing", f"{module}:two_args", "module_that_does_not_exist:fn"):
        spec = make_spec(module)
        spec["function"] = target
        result = run_property(spec, root)
        assert result["status"] == "error"
        assert result["evaluations"] == 0
        assert not result["has_counterexample"]


@pytest.mark.parametrize("change", [
    {"unknown": 1}, {"version": True}, {"rationale": " "}, {"domain": ""},
    {"function": "module:fn(x)"}, {"reference": "sample:square_bad"},
    {"strategy": {"type": "integers", "min_value": True}},
    {"strategy": {"type": "integers", "min_value": 2, "max_value": 1}},
    {"strategy": {"type": "text", "alphabet": "", "min_size": 1}},
    {"strategy": {"type": "text", "max_szie": 3}},
    {"strategy": {"type": "lists"}}, {"strategy": {"type": "one_of", "strategies": []}},
    {"strategy": {"type": "just", "value": float("nan")}},
])
def test_invalid_specs_fail_before_execution(change):
    spec = make_spec("sample")
    spec.update(change)
    with pytest.raises(SpecError):
        validate_spec(spec)


def test_strategy_source_is_executable_and_validation_does_not_mutate():
    strategy = {"type": "one_of", "strategies": [
        {"type": "lists", "elements": {"type": "integers", "min_value": 0, "max_value": 2}, "max_size": 3},
        {"type": "just", "value": {"text": "x'\\\ny", "flag": True, "nothing": None}},
        {"type": "booleans"},
    ]}
    snapshot = copy.deepcopy(strategy)
    built = build_strategy(strategy)
    generated = eval(strategy_source(strategy), {"st": st})
    assert str(built) == str(generated)
    assert strategy == snapshot


def test_json_load_rejects_duplicate_keys(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text('{"version": 1, "version": 2}', encoding="utf-8")
    with pytest.raises(SpecError, match="Duplicate"):
        load_spec(path)


def test_same_seed_same_shrunk_input(functions):
    root, module = functions
    spec = make_spec(module)
    first = run_property(spec, root, max_examples=100, seed=42)
    second = run_property(spec, root, max_examples=100, seed=42)
    assert first["counterexample"] == second["counterexample"] == -1
