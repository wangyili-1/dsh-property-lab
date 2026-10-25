# Local validation — 2026-10-25

This file records checks actually run while preparing version 0.1.0. Local results are listed below; remote GitHub Actions results are recorded separately when verified.

## Confirmed

- Publication check on 2026-10-25: the current Windows / Python 3.13.15 checkout passed **40 tests in 45.45 seconds**. A freshly built wheel includes the skill runner and excludes bytecode caches; explicit package-data exclusions prevent local `__pycache__` files entering new builds. Historical build output was moved aside before checking the new wheel.
- Windows, Python 3.13.15, Hypothesis 6.170.9: **40 tests passed**. Tests exercise the engine, real CLI subprocesses, timeout handling, error classification, code repair and replay, standalone exports, stale bytecode, source fingerprints, HTML escaping and installer ownership checks.
- Windows, Python 3.10, Hypothesis 6.168.5 (the version selected by pip for this interpreter): **40 tests passed** in a separate virtual environment.
- All six demo runs matched their expected outcomes: three deliberately buggy fixtures yielded reproducible counterexamples; three corrected versions had no counterexample in their configured search budgets.
- A wheel was built, installed into a separate virtual environment, and its demo and temporary DSH installation ran from outside the source checkout.
- The skill passed the skill-creator structural validator.
- The installed skill was discovered and loaded by the actual DSH **0.1.2-rc.1** filesystem provider as `user-dsh`, with model and user invocation enabled and no discovery warnings.
- The installed launcher executed the pinned Python interpreter successfully. It does not need an additional API key.
- An actual DSH **0.1.2-rc.1** headless model session completed using the official DeepSeek provider and `deepseek-flash` on 2026-10-25. The durable session trace confirms a successful `skill` tool call for `dsh-property-lab`, followed by the installed runner's `doctor` and `demo` commands, both exiting 0. All six demo outcomes matched expectations. This checks the model-to-skill execution path, not just filesystem discovery.
- That model-driven run read the generated summary and three buggy reports. Hypothesis shrank their inputs to `"+"`, three ASCII spaces, and `[0, -1]`; each counterexample reproduced three times. The three fixed fixtures had no counterexample within the configured budgets. One additional, optional read-only Python cross-check initially failed because of shell quoting; the model corrected the command and reran it successfully. The recorded trace retains both attempts.
- An independent skill-guided check used a separate integer-money formatting fixture, not the six bundled examples. It found and replayed an input of `10554679156284893` cents where floating-point formatting returned `105546791562848.94` instead of the documented `105546791562848.93`. Both exported tests failed on that implementation, and source hashes were unchanged. This was a constructed local fixture, not a finding in an external project.
- Real unmodified releases were checked in isolated environments: toml 0.10.2 (two reproducible roundtrip defects, including known issue #246), python-dotenv 1.2.4 (2,500 evaluations without a counterexample) and boltons 26.2.0 (two seeds, 3,000 evaluations each, without a counterexample). See the README and `case-studies/` for contracts, independent reproduction, versions, commands and portable evidence.
- A separate DSH model session loaded the skill and reran the four real-project specs. The toml and boltons observations matched. The initial DSH dotenv attempt returned **inconclusive / exit 2**, because temporary-directory access/cleanup failed with Windows permission errors. That historical attempt is retained in `case-studies/dsh-verification.json` and local evidence.
- After a scoped fixture-directory and exported-test cache fix, a new DSH session confirmed an active restricted token, inherited workspace ACLs, successful fixture I/O/cleanup, **2,500 evaluations with no counterexample / exit 0**, and **15 passing tests / exit 0**. No new fixture directories remained. The target package, spec, seed, budget and sandbox policy were unchanged. See `case-studies/dotenv/dsh-permission-fix.json`; the old failure record was not rewritten.
- The exported-test cache change passed all **9 tests in tests/test_cli.py** on Python 3.13.15, including independent exports and stale-bytecode repair. This focused recheck is separate from the original 40-test suite above.
- Additional real-release cases reproduced three defects: **humanize 4.16.0** changes integer `9007199254740993` when explicitly formatting zero decimal places (146 initial CLI evaluations); **xmltodict 1.0.4** changes comment `<` into literal `&lt;` (19 evaluations; known PR #423); **boltons 26.2.0** fails to consume the complete first separator run with `maxsplit=1` (`[0, None, None]`, 44 evaluations). All use unmodified releases, reviewed legal domains and independent public-API/oracle checks. Novelty of the humanize and boltons cases is not established.
- The three new exported regressions each fail as expected on the target releases. The humanize default-precision and xmltodict ordinary-text controls each complete 3,000 evaluations and their exported property tests pass. Upstream tests selected for comparison also pass: 34 humanize `intcomma` tests and 119 tests across two xmltodict modules. These are not claims that entire upstream suites were run.
- A fresh DSH 0.1.2-rc.1 / `deepseek-flash` session loaded the skill and executed those three cases plus the two controls under `workspace-write`. The five CLI exits were **1 / 0 / 1 / 0 / 1**, with evaluations **146 / 3,000 / 19 / 3,000 / 44**. Each counterexample reproduced three times. See `case-studies/counterexamples-dsh-verification.json` for durable call/result verification. Prepared source and spec hashes remained unchanged; raw `needs_review` reports were retained, with contract review documented separately.

## Not established

- Linux/macOS and remote GitHub Actions have not been executed in this local session.
- The automated browser preview rejected the local `file:` URL. Report data and HTML escaping were tested; screenshot/layout inspection was not completed.
- A bounded search with no counterexample is not a correctness proof. A reproduced counterexample still requires review of the proposed contract and input domain.

## Reproduce

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
python -m dsh_property_lab demo
python -m build
```

`requirements-dev.lock` records the dependency versions used for the local checks. Runtime evidence is written under the ignored `.property-lab/` directory; do not treat this summary as a substitute for inspecting a run's JSON and logs.

The local model-to-skill run is recorded in `.property-lab/dsh-verified-run.json`, `.property-lab/dsh-trace-verification.json`, and `.property-lab/dsh-verified-demo/`. These local artifacts are intentionally excluded from source archives. DSH supplies its own configured model credential; this project does not store it.

To verify discovery with a local DSH installation, supply its package directory explicitly:

```sh
node scripts/verify-dsh.mjs --dsh-package-root PATH/TO/node_modules/@deepseek-ai/dsh
```

This invokes DSH's own parser without calling a model or exposing credentials.
