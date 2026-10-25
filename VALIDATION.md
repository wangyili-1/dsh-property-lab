# Local validation — 2026-10-25

This file records checks actually run while preparing version 0.1.0. The GitHub Actions workflow is provided but has not run remotely; this repository has not been published.

## Confirmed

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
- A separate DSH model session loaded the skill and reran the four real-project specs. The toml and boltons observations matched. The DSH dotenv attempt returned **inconclusive / exit 2**, because temporary-directory cleanup failed with Windows permission errors. This does not invalidate the separate successful CLI run, but DSH execution of that filesystem-dependent case is not confirmed. The original failed attempt is retained in `case-studies/dsh-verification.json` and local evidence.

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
