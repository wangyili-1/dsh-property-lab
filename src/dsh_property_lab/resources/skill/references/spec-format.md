# Property specification, version 1

Every spec is JSON with `version: 1`, a short `name`, `kind`, `function`, `strategy`, `rationale` and `domain`. Import references use `module:callable`; the callable takes one positional argument. The target root and its `src/` directory are added to the worker's import search path.

```json
{
  "version": 1,
  "name": "codec-roundtrip",
  "kind": "roundtrip",
  "function": "codec:encode",
  "inverse": "codec:decode",
  "strategy": {"type": "text", "alphabet": "ab09 +%", "max_size": 40},
  "rationale": "README encoding contract requires exact decoding, including '+' and '%'.",
  "domain": "Strings up to 40 characters from the documented alphabet ab09 +%."
}
```

Choose the alphabet from the contract; do not copy the sample alphabet if it excludes relevant inputs. Omitting `alphabet` uses Hypothesis Unicode text.

| kind | Extra field | Assertion |
| --- | --- | --- |
| roundtrip | inverse | inverse(function(x)) == x |
| idempotence | none | function(function(x)) == function(x) |
| equivalence | reference | function(x) == reference(x) |

Both branches receive independent input copies. The executor uses Python equality. It does not support approximate numeric equality, async callables or arbitrary user-written assertion expressions in version 1.

| Strategy type | Fields |
| --- | --- |
| text | optional alphabet (string), min_size, max_size |
| integers | optional min_value, max_value |
| booleans | none |
| lists | elements (nested strategy), optional min_size, max_size |
| just | value (finite JSON value) |
| one_of | strategies (nonempty list of nested strategies) |

Example integer list: `{"type":"lists","elements":{"type":"integers","min_value":-20,"max_value":20},"max_size":15}`.

Unknown fields and duplicate JSON keys are rejected. Express valid domains directly in strategies; arbitrary filtering code and Python eval are not supported. If the contract needs an unsupported domain or assertion, explain the limitation rather than silently broadening it.

Reports preserve the spec, seed, dependency versions, source file hashes, candidate input and observations. `evaluations` includes Hypothesis predicate calls during shrinking; `max_examples` is a search setting rather than a total-call limit. Search failures may be shrunk, but global minimality is not guaranteed. `inconclusive` results must not be counted as passing checks.
