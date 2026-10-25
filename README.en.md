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

## Real open-source case studies

On 2026-10-25, five projects' current PyPI releases were tested on Windows 11, Python 3.13.15 and Hypothesis 6.170.9, in separate environments. **Three additional counterexamples in humanize, xmltodict and boltons bring the collection to five reproduced implementation defects**, including the earlier two toml cases. These are new cases for this repository, not claims of first discovery. Target code was not modified. Specifications follow upstream contracts and explicitly bound the input domain.

| Target | Property | Actual initial CLI evaluations | Observed result |
| --- | --- | --- | --- |
| [humanize 4.16.0](case-studies/humanize/README.md) | Integer grouping with explicit `ndigits=0` preserves the value | 146 | `9007199254740993` becomes `'9,007,199,254,740,992'`. Default-precision control: 3,000 evaluations without a violation. |
| [xmltodict 1.0.4](case-studies/xmltodict/README.md) | One legal XML comment roundtrips unchanged | 19 | Comment `'<'` becomes literal `'&lt;'`. Text-node control: 3,000 evaluations without a violation. |
| [boltons 26.2.0 split](case-studies/boltons-boundaries/README.md) | Grouped separators with `sep=None, maxsplit=1` | 44 | `[0, None, None]` returns `[[0], [None]]`, expected `[[0]]`; reproduced with a second seed. |
| [toml 0.10.2](case-studies/toml/README.md) | String and string-list roundtrips | 29 / 32 | U+001F causes an encoder `IndexError`; `['"']` roundtrips to `['']`. Both reproduce three times. |
| [python-dotenv 1.2.4](case-studies/dotenv/README.md) | Quoted values through public write/read APIs, interpolation disabled | 2,500 | No counterexample; after a fixture permission fix, DSH also completes 2,500 evaluations and 15 tests. |
| [boltons 26.2.0](case-studies/boltons/README.md) | Ordered integer deduplication vs an independent oracle | 3,000 | No counterexample; a second seed also completes 3,000 evaluations without a violation. |

The xmltodict comment result reproduces the defect addressed by existing [PR #423](https://github.com/martinblech/xmltodict/pull/423); the toml control-character result reproduces known [issue #246](https://github.com/uiri/toml/issues/246). Novelty and maintainer confirmation of the other three findings are not established. Independent checks use `Decimal`, the standard-library DOM, a `str.split(None, 1)` oracle and `tomllib`. All five exported regressions fail as expected on the unmodified targets. The boltons oracle preserves separators inside the unsplit remainder and excludes the explicitly special-cased `maxsplit=0` behavior. The two toml inputs also reproduce at the checked upstream HEAD; its latest release dates from 2020.

The original passing boltons deduplication case is retained: finding a defect in `split` does not invalidate the bounded result for `unique`. The new humanize and xmltodict controls each complete 3,000 evaluations. Meanwhile, 34 upstream humanize `intcomma` tests and the two checked xmltodict test modules (119 tests) still pass. These counts describe the selected upstream tests, not entire upstream suites.

A real DSH 0.1.2-rc.1 / `deepseek-flash` session loaded the skill and reran all four prepared specifications. The toml and boltons results matched. The initial dotenv attempt returned `inconclusive / 2`; its [original evidence](case-studies/dsh-verification.json) is retained.

A separate real DSH session reran the five new specifications: humanize defect/control, xmltodict defect/control, and boltons split. Actual evaluations were **146 / 3,000 / 19 / 3,000 / 44**, with exit codes **1 / 0 / 1 / 0 / 1**. All three counterexamples reproduced three times; both controls completed their budgets. The session used `workspace-write` and the prepared isolated environments, with a 3,000-example budget for each specification. [Durable trace verification](case-studies/counterexamples-dsh-verification.json) covers skill loading, commands and report reads. These were model-orchestrated reruns of reviewed specifications, not autonomous model discovery. Raw reports retain `classification: needs_review`; defect classification here reflects the subsequent independent contract and public-API review.

**The dotenv permission compatibility issue is now fixed and verified in DSH.** On Windows, Python 3.13's `mkdir(0o700)` drops the inherited workspace ACL. The synthetic fixture helper now creates a unique directory inheriting that ACL and still requires successful cleanup. Exported tests isolate bytecode using a unique path without creating a temporary directory. The target library, property, input domain and sandbox policy are unchanged. A new DSH probe records `restricted_token=true`, inherited ACLs, successful I/O and cleanup; the full run completes **2,500 evaluations, no counterexample, exit 0**, followed by **15 passing tests**, with no new fixture leftovers. See the [new verification](case-studies/dotenv/dsh-permission-fix.json).

Each linked case includes contract sources, fixed dependencies, commands, source hashes and a clearly labelled portable evidence summary. Raw local evidence is retained separately; no upstream issues or PRs were submitted. Counts include shrinking and can overlap across runs. No-counterexample is not a correctness proof, and environment failures are not upstream bugs.

The new DSH trace also records two narrative inaccuracies: the extra second boltons group was called a third empty group, and a control's ability to rule out domain/generator problems was overstated. Execution and report checks passed; the summary above relies on the raw evidence and independent review, not those model descriptions.

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
