# dsh-property-lab

[中文](README.md)

A local **Python + Hypothesis** execution companion for DeepSeek Harness (DSH). DSH reads your code and proposes a justified property and input domain. The runner executes that specification, shrinks counterexamples, and exports reproducible evidence and tests. The CLI does not call an LLM or require a model API key.

## Supported properties

| Kind | Assertion |
| --- | --- |
| `roundtrip` | `inverse(function(x)) == x` |
| `idempotence` | `function(function(x)) == function(x)` |
| `equivalence` | `function(x) == reference(x)` |

Version 1 supports synchronous functions taking one positional argument and JSON-compatible inputs: text, integers, booleans, lists, fixed values, and combinations of strategies. Each specification must explain its contract in `rationale` and its valid input domain in `domain`.

## Install

Python **3.10+** is required. Use a dedicated virtual environment and install the target project's dependencies in the same environment.

Windows PowerShell, from the repository root:

```powershell
.\scripts\setup.ps1
.\.venv\Scripts\python.exe -m dsh_property_lab doctor
.\.venv\Scripts\python.exe -m dsh_property_lab install-dsh
```

macOS / Linux:

```sh
sh scripts/setup.sh
.venv/bin/python -m dsh_property_lab doctor
.venv/bin/python -m dsh_property_lab install-dsh
```

Alternatively, use `python -m pip install -e ".[dev]"` in an existing environment.

`install-dsh` copies the skill to DSH's user skill directory and creates an entry point using the installed interpreter. It does not edit a DSH profile. Use `--dsh-home PATH` for a custom home. Reinstall after moving this repository or replacing its virtual environment. The compatibility target includes the local skill mechanism in desktop DSH `0.1.2-rc.1`.

In a new DSH conversation, ask:

> Use dsh-property-lab to inspect this Python codec. Derive a roundtrip property from the docs and existing tests, explain the input domain, execute the spec, and save a counterexample and regression test. Do not change production code.

## Try the demo

```sh
python -m dsh_property_lab demo
python -m dsh_property_lab run examples/roundtrip-buggy.json --project . --seed 2026 --max-examples 300 --timeout 60
```

The demo contains three deliberately faulty teaching examples and their corrected counterparts: a form encoder that fails to escape literal `+`, a space normalizer that performs only one replacement pass, and a deduplicator that mistakenly sorts its output. These are not discoveries in third-party software.

## Your project

Create a JSON specification, using the examples as templates:

```json
{
  "version": 1,
  "name": "encoding-roundtrip",
  "kind": "roundtrip",
  "function": "codec:encode",
  "inverse": "codec:decode",
  "strategy": {
    "type": "text",
    "alphabet": "ab09 +%",
    "min_size": 0,
    "max_size": 40
  },
  "rationale": "The documented codec contract promises to recover the original text, including spaces and plus signs.",
  "domain": "Strings of length 0 through 40 drawn from ab09 +%."
}
```

```sh
python -m dsh_property_lab run encoding-property.json --project /path/to/project
```

Callable names use `module:function`. The project root is added to the target process's import path. Install projects with a `src` layout into the same environment first. The runner does not install target dependencies or modify production code.

## Evidence and replay

The CLI prints the report directory. The default is `.property-lab/runs/`, ignored by Git; override it with `--output DIR`, using a new or empty directory to preserve earlier evidence. Reports are emitted as `report.json`, `report.md`, and `report.html`, including the specification, seed, runtime versions, source hashes, and observations. Captured output is kept in `worker.log` and `process.log`; these can be empty. Valid specifications also export `test_property.py`; reproducible counterexamples additionally export `test_regression.py`.

```sh
python -m dsh_property_lab replay /path/to/report.json --project /path/to/project
python -m pytest /path/to/test_regression.py
```

Run exported tests from the tested project root, or set `PROPERTY_LAB_PROJECT` to that root, in an environment with the target dependencies installed. Regression tests should fail against the defective code and pass after the code is fixed. A changed target version can change replay results.

| Status | Meaning | `run` exit code |
| --- | --- | --- |
| `counterexample` | A reproducible property violation requiring review | `1` |
| `no_counterexample` | No counterexample found within this search budget | `0` |
| `inconclusive` / `error` | A reliable conclusion could not be reached | `2` |

No counterexample is not proof of correctness. A failure may reveal a mistaken property, an invalid input domain, or a code defect. Shrinking is not a guarantee of global minimality. Generation and shrinking may call the target more times than `--max-examples`; `--timeout` bounds the worker process's elapsed runtime.

## Limits

Run only trusted local code: importing and testing a Python module executes it. A subprocess and timeout are **not a security sandbox**. Targets should be repeatable and avoid external side effects. This version does not cover async functions, multiple arguments, arbitrary Python objects, or browser tests. Reports can contain target data and should be reviewed before publication.

## Develop

```sh
python -m pip install -e ".[dev]"
python -m pytest
```

The repository includes a GitHub Actions test workflow and does not assume a GitHub account or remote URL.

## License and acknowledgments

The implementation and skill instructions are independently written and [MIT licensed](LICENSE). The runner uses [Hypothesis](https://hypothesis.readthedocs.io/). The project direction was inspired by the [Trail of Bits property-based-testing skill](https://github.com/trailofbits/skills/tree/main/plugins/property-based-testing); its skill text and scripts are not copied here. That upstream project retains its own CC-BY-SA-4.0 license.
