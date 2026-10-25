"""Portable tests and static reports, derived only from recorded execution results."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .spec import strategy_source

LABELS = {"counterexample": "Counterexample found / 发现反例", "no_counterexample": "No counterexample found / 未找到反例",
          "inconclusive": "Inconclusive / 无法判定", "error": "Execution error / 执行失败"}


def dump_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def property_helper(spec: dict) -> str:
    """Export independently executable assertions, with no dependency on this package."""
    base = '''from copy import deepcopy
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

'''
    base += f"_function = _load({spec['function']!r})\n"
    if spec["kind"] == "roundtrip":
        base += f"_inverse = _load({spec['inverse']!r})\n\ndef _assert_property(value):\n    expected = deepcopy(value)\n    actual = _inverse(_function(deepcopy(value)))\n    assert actual == expected, (actual, expected)\n"
    elif spec["kind"] == "idempotence":
        base += "\ndef _assert_property(value):\n    once = _function(deepcopy(value))\n    expected = deepcopy(once)\n    actual = _function(deepcopy(once))\n    assert actual == expected, (actual, expected)\n"
    else:
        base += f"_reference = _load({spec['reference']!r})\n\ndef _assert_property(value):\n    expected = _reference(deepcopy(value))\n    actual = _function(deepcopy(value))\n    assert actual == expected, (actual, expected)\n"
    return base


def write_tests(report: dict, directory: Path) -> None:
    spec = report["spec"]
    comment = "# Generated from a recorded property specification. Review the property before adopting it.\n"
    comment += "# Contract: " + spec["rationale"].replace("\n", " ").replace("\r", " ") + "\n"
    helper = property_helper(spec)
    test = comment + "from hypothesis import given, settings, seed, example, strategies as st\n" + helper
    if report.get("has_counterexample"):
        test += f"\n@example(value={report['counterexample']!r})\n"
    else:
        test += "\n"
    test += (f"@seed({report['seed']!r})\n"
             f"@settings(max_examples={report['max_examples']!r}, deadline=None, database=None)\n"
             f"@given(value={strategy_source(spec['strategy'])})\n"
             "def test_property(value):\n    _assert_property(value)\n\n"
             "if __name__ == '__main__':\n    test_property()\n")
    (directory / "test_property.py").write_text(test, encoding="utf-8")
    if report.get("has_counterexample"):
        regression = (comment + helper + f"\nCOUNTEREXAMPLE = {report['counterexample']!r}\n\n"
                      "def test_regression():\n    _assert_property(COUNTEREXAMPLE)\n\n"
                      "if __name__ == '__main__':\n    test_regression()\n")
        (directory / "test_regression.py").write_text(regression, encoding="utf-8")


STYLE = """
:root{color-scheme:light;--ink:#172b45;--muted:#52647c;--line:#dbe4ee}
*{box-sizing:border-box}body{margin:0;background:#f4f7fb;color:var(--ink);font:16px/1.6 system-ui,'Segoe UI',sans-serif}
main{max-width:1080px;margin:40px auto;padding:0 24px 50px}.eyebrow{font-size:12px;font-weight:750;letter-spacing:.14em;color:#4160b6}
h1{font-size:36px;line-height:1.2;margin:12px 0}h2{font-size:19px;margin-top:0}.muted{color:var(--muted)}
.badge{display:inline-block;border-radius:99px;padding:6px 14px;font-weight:700;background:#e1eaf9;font-size:14px}
.counterexample{background:#fff0d4;color:#805300}.no_counterexample{background:#dff4eb;color:#176343}.error,.inconclusive{background:#fbe2e6;color:#8b2942}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;margin:24px 0}.card,section{background:white;border:1px solid var(--line);border-radius:16px;padding:22px;min-width:0}
.value{font-size:25px;font-weight:700}.small{font-size:13px}section{margin:18px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fb;border-radius:10px;padding:16px;font:13px/1.65 Consolas,monospace}
code{overflow-wrap:anywhere}a{color:#2857aa}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:12px;border-bottom:1px solid var(--line);vertical-align:top}footer{font-size:13px;color:var(--muted);margin-top:24px}
@media(max-width:600px){main{margin:24px auto;padding:0 14px 30px}h1{font-size:28px}.card,section{padding:16px}}
"""


def page(title: str, body: str) -> str:
    return f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLE}</style><main><div class="eyebrow">DSH PROPERTY LAB · EXECUTION EVIDENCE</div>{body}<footer>Generated from local execution. A counterexample needs contract review; a bounded search is not a proof.</footer></main></html>'


def write_report(report: dict, directory: Path) -> None:
    dump_json(directory / "report.json", report)
    spec = report["spec"]
    status = report["status"]
    shown = json.dumps(report.get("counterexample"), ensure_ascii=True) if report.get("has_counterexample") else "—"
    note = ("Review required: implementation defect, incorrect property, or invalid input domain."
            if report.get("has_counterexample") else
            "No counterexample found within this search budget; this is not a proof of correctness."
            if status == "no_counterexample" else "Execution did not establish a reliable property result.")
    detail = report.get("observation") or report.get("error") or report.get("message") or {}
    rendered = json.dumps(detail, ensure_ascii=True, indent=2)
    esc = html.escape
    cards = "".join(f'<div class="card"><div class="muted small">{esc(key)}</div><div class="value">{esc(str(value))}</div></div>'
                    for key, value in [("Property", spec["kind"]), ("Evaluations incl. shrinking", report.get("evaluations") if report.get("evaluations") is not None else "unknown"), ("Seed", report["seed"]), ("Seconds", report.get("duration_seconds", "—"))])
    body = (f'<h1>{esc(spec["name"])}</h1><span class="badge {status}">{esc(LABELS.get(status,status))}</span>'
            f'<p class="muted">{esc(note)}</p><div class="grid">{cards}</div>'
            f'<section><h2>Contract / 性质依据</h2><p>{esc(spec["rationale"])}</p><p class="muted">Input domain: {esc(spec["domain"])}</p><code>{esc(spec["function"])}</code></section>'
            f'<section><h2>Counterexample / 缩减后的反例</h2><pre>{esc(shown)}</pre><p class="muted small">Shrunk by Hypothesis when a counterexample is found; no claim of global minimality.</p><pre>{esc(rendered)}</pre></section>'
            f'<section><h2>Evidence &amp; reproduction</h2><p><a href="report.json">report.json</a> · <a href="spec.json">spec.json</a> · <a href="worker.log">worker.log</a> · <a href="test_property.py">test_property.py</a>'
            + (' · <a href="test_regression.py">test_regression.py</a>' if report.get("has_counterexample") else '')
            + f'</p><pre>{esc(json.dumps(report.get("runtime", {}), ensure_ascii=True, indent=2))}</pre><p class="small muted">Project: {esc(report["project"])}<br>Recorded: {esc(report["started_at"])}</p></section>')
    (directory / "report.html").write_text(page(spec["name"], body), encoding="utf-8")
    md = (f'# {spec["name"]}\n\n**{LABELS.get(status,status)}**\n\n{note}\n\n'
          f'Property: `{spec["kind"]}` · Seed: `{report["seed"]}` · Evaluations: `{report.get("evaluations",0)}`\n\n'
          f'Contract: {spec["rationale"]}\n\nDomain: {spec["domain"]}\n\n'
          f'Counterexample (Hypothesis-shrunk, not guaranteed globally minimal):\n\n```json\n{shown}\n```\n\n'
          f'Observation:\n\n```json\n{rendered}\n```\n\n'
          'Run exported tests from the project root, or set `PROPERTY_LAB_PROJECT`. '
          'Keep the JSON report and source fingerprints with the tests.\n')
    (directory / "report.md").write_text(md, encoding="utf-8")


def write_demo_index(rows: list[dict], directory: Path) -> None:
    table = ''.join(f'<tr><td><a href="{html.escape(row["directory"])}/report.html">{html.escape(row["name"])}</a></td><td>{html.escape(row["expected"])}</td><td>{html.escape(row["status"])}</td><td>{"PASS" if row["matched"] else "FAIL"}</td></tr>' for row in rows)
    body = ('<h1>Find it. Shrink it. Replay it.</h1><p class="muted">Three deliberately buggy fixtures and their corrected implementations. These are demonstration cases, not discoveries in external projects.</p>'
            f'<div class="grid"><div class="card"><div class="muted small">Expected outcomes matched</div><div class="value">{sum(row["matched"] for row in rows)} / {len(rows)}</div></div></div>'
            '<section><h2>Local Hypothesis execution</h2><table><thead><tr><th>Fixture</th><th>Expected</th><th>Observed</th><th>Check</th></tr></thead><tbody>' + table + '</tbody></table></section>')
    (directory / "index.html").write_text(page("DSH Property Lab · Demo", body), encoding="utf-8")
    dump_json(directory / "summary.json", rows)
