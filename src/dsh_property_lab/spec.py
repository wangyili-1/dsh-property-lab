"""Validate the small, declarative property format used by Property Lab.

Specifications contain data and import references, never Python expressions.
Importing and calling the referenced project is the execution worker's job.
"""

from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from typing import Any

from hypothesis import strategies as st


class SpecError(ValueError):
    """A property or input domain cannot be interpreted unambiguously."""


_REFERENCE = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")
_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}$")
_FIELDS = {
    "text": {"type", "alphabet", "min_size", "max_size"},
    "integers": {"type", "min_value", "max_value"},
    "booleans": {"type"},
    "lists": {"type", "elements", "min_size", "max_size"},
    "just": {"type", "value"},
    "one_of": {"type", "strategies"},
}


def _unknown(value: dict, allowed: set[str], location: str) -> None:
    extra = set(value) - allowed
    if extra:
        raise SpecError(f"{location}: unknown field(s): {', '.join(sorted(map(str, extra)))}")


def _json_value(value: Any, location: str, depth: int = 0) -> None:
    if depth > 32:
        raise SpecError(f"{location}: JSON nesting exceeds 32 levels")
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float) and math.isfinite(value):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _json_value(item, f"{location}[{index}]", depth + 1)
        return
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        for key, item in value.items():
            _json_value(item, f"{location}.{key}", depth + 1)
        return
    raise SpecError(f"{location}: expected a finite, JSON-serializable value")


def _integer(value: Any, location: str, *, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        suffix = f" >= {minimum}" if minimum is not None else ""
        raise SpecError(f"{location}: expected an integer{suffix}")
    return value


def validate_strategy(value: Any, location: str = "strategy", depth: int = 0) -> dict:
    if depth > 16:
        raise SpecError(f"{location}: strategy nesting exceeds 16 levels")
    if not isinstance(value, dict):
        raise SpecError(f"{location}: expected an object")
    kind = value.get("type")
    if not isinstance(kind, str) or kind not in _FIELDS:
        raise SpecError(f"{location}.type: choose {', '.join(_FIELDS)}")
    _unknown(value, _FIELDS[kind], location)
    if kind in {"text", "lists"}:
        for key in ("min_size", "max_size"):
            if key in value:
                _integer(value[key], f"{location}.{key}", minimum=0)
        if "max_size" in value and value.get("min_size", 0) > value["max_size"]:
            raise SpecError(f"{location}: min_size must not exceed max_size")
    if kind == "text" and "alphabet" in value:
        if not isinstance(value["alphabet"], str):
            raise SpecError(f"{location}.alphabet: expected a string of allowed characters")
        if not value["alphabet"] and value.get("min_size", 0) > 0:
            raise SpecError(f"{location}: an empty alphabet cannot satisfy min_size > 0")
    if kind == "integers":
        for key in ("min_value", "max_value"):
            if key in value:
                _integer(value[key], f"{location}.{key}")
        if "min_value" in value and "max_value" in value and value["min_value"] > value["max_value"]:
            raise SpecError(f"{location}: min_value must not exceed max_value")
    if kind == "lists":
        if "elements" not in value:
            raise SpecError(f"{location}.elements: required for lists")
        validate_strategy(value["elements"], f"{location}.elements", depth + 1)
    if kind == "just":
        if "value" not in value:
            raise SpecError(f"{location}.value: required for just")
        _json_value(value["value"], f"{location}.value")
    if kind == "one_of":
        choices = value.get("strategies")
        if not isinstance(choices, list) or not choices:
            raise SpecError(f"{location}.strategies: expected a non-empty list")
        for index, choice in enumerate(choices):
            validate_strategy(choice, f"{location}.strategies[{index}]", depth + 1)
    return copy.deepcopy(value)


def validate_spec(value: Any) -> dict:
    if not isinstance(value, dict):
        raise SpecError("spec: expected an object")
    allowed = {"version", "name", "kind", "function", "inverse", "reference", "strategy", "rationale", "domain"}
    _unknown(value, allowed, "spec")
    if type(value.get("version")) is not int or value["version"] != 1:
        raise SpecError("version: expected 1")
    if not isinstance(value.get("name"), str) or not _NAME.fullmatch(value["name"]):
        raise SpecError("name: use 1-80 letters, numbers, underscores or hyphens; start with a letter or number")
    kind = value.get("kind")
    if kind not in ("roundtrip", "idempotence", "equivalence"):
        raise SpecError("kind: choose roundtrip, idempotence or equivalence")
    reference_fields = ["function"]
    if kind == "roundtrip":
        reference_fields.append("inverse")
        if "reference" in value:
            raise SpecError("reference: only valid for equivalence")
    elif kind == "equivalence":
        reference_fields.append("reference")
        if "inverse" in value:
            raise SpecError("inverse: only valid for roundtrip")
    elif "inverse" in value or "reference" in value:
        raise SpecError("idempotence: inverse and reference are not used")
    for field in reference_fields:
        if not isinstance(value.get(field), str) or not _REFERENCE.fullmatch(value[field]):
            raise SpecError(f"{field}: expected 'python.module:callable_name'")
    if kind == "equivalence" and value["function"] == value["reference"]:
        raise SpecError("reference: comparing a function with itself is not an independent equivalence property")
    for field in ("rationale", "domain"):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise SpecError(f"{field}: a non-empty explanation is required")
    if "strategy" not in value:
        raise SpecError("strategy: required")
    validate_strategy(value["strategy"])
    return copy.deepcopy(value)


def load_spec(path: str | Path) -> dict:
    def reject_constant(token: str) -> None:
        raise SpecError(f"Non-finite JSON value {token!r} is not supported")

    def unique_object(pairs: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in pairs:
            if key in result:
                raise SpecError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result

    try:
        text = Path(path).read_text(encoding="utf-8-sig")
        value = json.loads(text, parse_constant=reject_constant, object_pairs_hook=unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpecError(f"Cannot read spec {path}: {exc}") from exc
    return validate_spec(value)


def build_strategy(value: dict):
    value = validate_strategy(value)
    kind = value["type"]
    if kind == "lists":
        return st.lists(build_strategy(value["elements"]), **{k: value[k] for k in ("min_size", "max_size") if k in value})
    if kind == "one_of":
        return st.one_of(*(build_strategy(choice) for choice in value["strategies"]))
    if kind == "just":
        return st.just(copy.deepcopy(value["value"]))
    return getattr(st, kind)(**{key: item for key, item in value.items() if key != "type"})


def strategy_source(value: dict) -> str:
    """Return standalone Python source using the conventional ``st`` alias."""
    value = validate_strategy(value)
    kind = value["type"]
    if kind == "lists":
        args = [strategy_source(value["elements"])]
        args.extend(f"{key}={value[key]!r}" for key in ("min_size", "max_size") if key in value)
    elif kind == "one_of":
        args = [strategy_source(choice) for choice in value["strategies"]]
    elif kind == "just":
        args = [repr(value["value"])]
    else:
        args = [f"{key}={item!r}" for key, item in value.items() if key != "type"]
    return f"st.{kind}({', '.join(args)})"
