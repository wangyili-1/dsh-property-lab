# dsh-property-lab

[中文](README.md)

A local **Python + Hypothesis** execution companion for DeepSeek Harness (DSH): search boundary inputs, shrink failures, and export reproducible tests. The CLI does not call an LLM or require a model API key.

## Three real counterexamples

**An integer changes value, an XML comment changes content, and a grouped separator leaks into the result.** These differences were reproduced on unmodified open-source releases, with reviewed contracts, independent checks, and exported regression tests. No first-discovery claim is made. After installing the pinned dependencies in each case study, the public APIs show the failures directly:

```python
import humanize  # 4.16.0
import xmltodict  # 1.0.4
from boltons.iterutils import split  # boltons 26.2.0

# Grouping an integer changes its last digit; default ndigits=None preserves it.
humanize.intcomma(9007199254740993, 0)  # '9,007,199,254,740,992'
# Expected: '9,007,199,254,740,993'

# Entity references inside XML comments are literal text.
encoded = xmltodict.unparse({'root': {'#comment': '<'}})
xmltodict.parse(encoded, process_comments=True, strip_whitespace=False)['root']['#comment']
# Actual: '&lt;'
# Expected: '<'

# Consecutive None values should form one separator run.
split([0, None, None], sep=None, maxsplit=1)  # [[0], [None]]
# Expected under the documented str.split grouping semantics: [[0]]
```

[humanize: reproduction and precision control](case-studies/humanize/README.md) · [xmltodict: reproduction and text control](case-studies/xmltodict/README.md) · [boltons: contract and independent oracle](case-studies/boltons-boundaries/README.md)

## Real open-source case studies

On 2026-10-25, five projects' latest stable PyPI releases as of that date were tested on Windows 11, Python 3.13.15 and Hypothesis 6.170.9, in separate environments. **Five implementation defects were reproduced.** Target code was not modified; this repository supplies thin adapters, independent reference implementations, and reviewed specifications with explicit input domains. Results without a counterexample are retained alongside the failures.

| Target | Property | Actual initial CLI evaluations | Observed result |
| --- | --- | --- | --- |
| [humanize 4.16.0](case-studies/humanize/README.md) | Integer grouping with explicit `ndigits=0` preserves the value | 146 | `9007199254740993` becomes `'9,007,199,254,740,992'`. Default-precision control in the same domain: 3,000 evaluations without a violation. |
| [xmltodict 1.0.4](case-studies/xmltodict/README.md) | One legal XML comment roundtrips unchanged | 19 | Comment `'<'` becomes literal `'&lt;'`. Text-node control with the same character domain: 3,000 evaluations without a violation. |
| [boltons 26.2.0 split](case-studies/boltons-boundaries/README.md) | Grouped separators with `sep=None, maxsplit=1` | 44 | `[0, None, None]` returns `[[0], [None]]`, expected `[[0]]`; reproduced with a second seed. |
| [toml 0.10.2](case-studies/toml/README.md) | String and string-list roundtrips | 29 / 32 | U+001F causes an encoder `IndexError`; `['"']` roundtrips to `['']`. Both reproduce three times. |
| [python-dotenv 1.2.4](case-studies/dotenv/README.md) | Quoted values through public write/read APIs, interpolation disabled | 2,500 | No counterexample; DSH reproduces this result after a fixture permission compatibility fix. |
| [boltons 26.2.0 unique](case-studies/boltons/README.md) | Ordered integer deduplication vs an independent oracle | 3,000 | No counterexample; a second seed also completes 3,000 evaluations without a violation. |

**Known issues and novelty:** the xmltodict comment result reproduces the defect addressed by existing [PR #423](https://github.com/martinblech/xmltodict/pull/423); the toml control-character result reproduces known [issue #246](https://github.com/uiri/toml/issues/246). Novelty and maintainer confirmation of the other three findings are not established. The two toml inputs also reproduce at the upstream HEAD recorded in the case study; release 0.10.2 dates from 2020. No upstream issues or PRs were submitted.

### How the findings were checked

Official documentation, source, and existing tests were reviewed before specifying legal input domains and running the actual CLI with seed `20261025`. Counterexamples were replayed and checked through public APIs and exported tests. All five exported regressions fail as expected on the unmodified targets. Independent checks use `Decimal` for humanize, the standard-library DOM for xmltodict, and `tomllib` for toml.

The boltons reference follows `str.split(None, 1)`, preserves separators inside the unsplit remainder, and excludes the explicitly special-cased `maxsplit=0` behavior. It was also cross-checked against a separate positional-scan algorithm over 5,461 finite-domain lists. The property does not require every output group to be free of separators.

Selected upstream tests still pass: 34 humanize `intcomma` tests and 119 tests across two xmltodict modules. These counts describe the selected tests, not entire upstream suites; they did not cover the observed boundaries. The bounded no-counterexample result for boltons `unique` is retained separately from the defect in `split`.

### Real DSH execution evidence

A real DSH `0.1.2-rc.1` / `deepseek-flash` session loaded the skill and ran humanize defect/control, xmltodict defect/control, and boltons split, in that order. It used `workspace-write`, isolated environments, and a 3,000-example budget per specification. Actual evaluations were **146 / 3,000 / 19 / 3,000 / 44**, with exit codes **1 / 0 / 1 / 0 / 1**. All three counterexamples reproduced internally three times. [Durable trace verification](case-studies/counterexamples-dsh-verification.json) covers skill loading, actual commands, report reads, and file hashes. **These were model-orchestrated reruns of prewritten, reviewed specifications; the evidence does not establish autonomous model discovery of properties.**

The [DSH record for toml, dotenv, and boltons unique](case-studies/dsh-verification.json) retains the initial dotenv `inconclusive / 2` result caused by temporary-directory permissions. After a Windows compatibility fix to fixture directories and exported-test caching, DSH completed **2,500 evaluations, no counterexample, exit 0**, followed by **15 passing tests**, with the same property, domain, seed, budget, and sandbox policy. This was an environment fix, not an upstream defect. See the [case details](case-studies/dotenv/README.md#dsh-受限环境修复与复验) and [verification record](case-studies/dotenv/dsh-permission-fix.json).

Raw CLI reports retain `classification: needs_review`; the defect classifications here reflect subsequent independent contract and public-API review. The DSH trace also records two inaccuracies in the model's prose about the boltons result and the controls' evidentiary strength. Those descriptions were not used as evidence for the conclusions above.

Each case includes fixed dependencies, commands, specifications, and a portable evidence summary with source/report SHA-256 hashes and labelled local-path substitutions. Raw local evidence is retained separately. Counts include generation and shrinking and can overlap across runs; they are not counts of unique inputs. No-counterexample is not a correctness proof. Core tests, case tests, upstream defect reproductions, and environment failures are recorded separately. See [VALIDATION.md](VALIDATION.md) for local checks and unverified scope.

## How it works

DSH reads code, documentation, and existing tests to propose a justified property and input domain. The local runner executes the JSON specification with Hypothesis, shrinks failures, and exports reports and tests.

| Kind | Assertion |
| --- | --- |
| `roundtrip` | `inverse(function(x)) == x` |
| `idempotence` | `function(function(x)) == function(x)` |
| `equivalence` | `function(x) == reference(x)` |

Version 1 supports synchronous functions taking one positional argument and JSON-compatible inputs: text, integers, booleans, lists, fixed values, and combinations of strategies. Each specification must explain its contract in `rationale` and its valid input domain in `domain`.

## Install

Python **3.10+** is required. Use a dedicated virtual environment and install the target project's dependencies in the same environment.

Clone the repository:

```sh
git clone https://github.com/wangyili-1/dsh-property-lab.git
cd dsh-property-lab
```

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

The repository includes a [GitHub Actions test workflow](.github/workflows/ci.yml). Local validation does not establish that remote CI has passed; actual runs appear on the repository's [Actions page](https://github.com/wangyili-1/dsh-property-lab/actions).

## License and acknowledgments

The implementation and skill instructions are independently written and [MIT licensed](LICENSE). The runner uses [Hypothesis](https://hypothesis.readthedocs.io/). The project direction was inspired by the [Trail of Bits property-based-testing skill](https://github.com/trailofbits/skills/tree/main/plugins/property-based-testing); its skill text and scripts are not copied here. That upstream project retains its own CC-BY-SA-4.0 license.
