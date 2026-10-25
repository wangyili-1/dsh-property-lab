---
name: dsh-property-lab
description: Test local Python functions with Hypothesis, shrink counterexamples and export reproducible regression tests. Use for encoder/decoder roundtrips, normalization idempotence or comparison with a reference implementation.
---

# DSH Property Lab

Read the relevant project code, documentation and existing tests, then propose an executable property grounded in that evidence. The bundled runner executes Hypothesis; it does not infer a contract or call a model itself.

## Workflow

1. Identify the target project root and a synchronous callable accepting one positional argument. Read its contract and valid input domain. This version supports `roundtrip`, `idempotence` and `equivalence`; if none fits, explain the limitation and use ordinary tests instead of inventing a property.
2. Write a JSON specification under the target project's `.property-lab/specs/`. Include a concrete `rationale` citing the relevant documentation or tests, and a `domain` explaining admissible inputs. Read [the specification format](references/spec-format.md) when authoring the JSON. A reference implementation must be independent of the target; avoid assertions that merely repeat its code.
3. Run `run <spec.json> --project <absolute-project-root>` through the installed runner. Use the pinned interpreter shown in the installed runtime section. Quote paths with spaces. If target dependencies are missing, report the exact missing dependency and use the project's intended environment or install the needed dependency within the user's authorized setup scope.
4. Inspect `report.json` and the actual execution logs. A `counterexample` is a violated proposed contract, not yet a proven implementation defect. Classify the cause as an implementation defect, wrong property, invalid domain, or unresolved. Do not weaken the property or modify business code just to make a run pass. Keep changed specifications and reruns in separate evidence directories.
5. Report the shrunk input, contract evidence, observed result and report path. Preserve `test_regression.py` and `test_property.py`; run them from the project root (or set `PROPERTY_LAB_PROJECT`). When the user asks for a fix, apply it and run the same saved regression test and property again, preserving both before and after results.

## Commands

Invoke the installed `scripts/run.py` with the pinned Python interpreter; its `runtime.json` selects the executor's environment. It preserves the working directory and arguments.

- `doctor`: inspect runtime and skill installation; does not call a model.
- `demo`: run six deliberately buggy/fixed fixtures and create an HTML summary.
- `run <spec> --project <path> --seed 2026 --max-examples 300 --timeout 60`: search and shrink in a fresh worker.
- `replay <report.json> --project <path>`: replay the exact saved counterexample, optionally against the repaired project.
- `--output <directory>` on run/replay/demo: preserve evidence in a new or empty directory.

Exit code `1` from run/replay means a counterexample was reproduced; it is not a tool crash. Code `0` means the selected search or replay found no violation; it is not proof of universal correctness. Code `2` means an error or inconclusive result. Inspect the report before deciding what to do next.

The target is imported and may be called repeatedly; use trusted local projects. The worker timeout is not a security sandbox. Prefer deterministic functions without network or filesystem side effects. Runtime exceptions can indicate an invalid input domain rather than a bug. Never describe fixture results or model reasoning as findings from a different project.
