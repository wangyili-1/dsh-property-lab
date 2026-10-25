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
- An independent skill-guided check used a separate integer-money formatting fixture, not the six bundled examples. It found and replayed an input of `10554679156284893` cents where floating-point formatting returned `105546791562848.94` instead of the documented `105546791562848.93`. Both exported tests failed on that implementation, and source hashes were unchanged. This was a constructed local fixture, not a finding in an external project.

## Not established

- A real DSH headless model run was attempted, but the configured API provider rejected its existing credentials with an authentication error before the task ran. This does not invalidate the local execution or discovery checks, but **full model-to-skill execution is not confirmed**. Configure a working credential in DSH, then ask it to use `/dsh-property-lab` and run `demo`.
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

To verify discovery with a local DSH installation, supply its package directory explicitly:

```sh
node scripts/verify-dsh.mjs --dsh-package-root PATH/TO/node_modules/@deepseek-ai/dsh
```

This invokes DSH's own parser without calling a model or exposing credentials.
