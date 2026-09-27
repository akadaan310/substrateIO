# Instrument report: computational addresses (PURL, provisional)

Not a research phase: no research state is added, and no hypothesis,
evidence or discovery changes. It adds an instrument, and records what
building and running it showed. Terms: C-037 … C-040. Queue: Q-013.

## BEFORE

R2. The substrate's objects (`StateSpace`, `DeterministicMap`, `Trace`,
functional graphs, projections, interventions) existed only as Python
values inside experiments. They could not be named, inspected or navigated
from outside a Python process. A design brief (relayed from a ChatGPT
session through the ACSP field-trial resource, P-006/P-007 and the follow-up
brief) asked for "PURL": addresses that expose computational structure and
return further addresses.

## QUESTION

What is the smallest addressing layer that makes the *existing* objects
addressable, self-describing and navigable, without a second ontology and
without breaking the research discipline?

## ACTION

Read the charter, ontology, protocol, nomenclature and every instrument. Then:

* `substrate/purl.py`: an operation registry and a resolver. An address is
  a **derivation path**: a root constructor, then operations, each
  dispatched on the *kind* of the object its prefix denotes. Kinds are O-1
  objects only: space, state, map, trace, graph, cycle, projection, damage
  (plus spectrum, declared).
* `substrate/purl_store.py`: append-only execution records (POST only),
  rerun comparison, extensional-equivalence observations, and
  content-addressed navigation trails.
* `tools/purl_server.py`: stdlib HTTP.
* `tests/test_purl.py`: 14 tests.
* Fixed an existing defect: `artifacts.code_hash()` left every source file
  open.

## OBSERVATION (from running it)

1. **The objects already had addresses.** Maps are extensional ("a map *is*
   its table", core.py) and deterministically constructible from
   parameters, so a path of constructor + operations *denotes* a value. No
   identifier store is needed; the address is the derivation. Formally an
   address is a **ground term** over a many-sorted signature (C-037). The
   PURL name is a working label.
2. **Lazy materialization already existed in miniature.** `eca_step`
   computes one transition without the 2^n table. So
   `/map/eca/30/40/state/5/next` resolves (x → 549755813901) while
   `/map/eca/30/40/graph` is refused with `409 not_materialized` (2^40
   states > 2^16 limit). That is charter rule 7, "not computed ≠ does not
   exist", as an HTTP status. Seeded random maps need the full table even
   for one step; the registry says so (`materializes`).
3. **Known ≠ executable.** `numpy.map.spectrum` is registered and fully
   described, and every manifest lists it, but NumPy is absent. It returns
   `501 unavailable_here` with the contract and `missing: ["numpy"]`.
   Existence, description and executability are three fields, not one
   boolean.
4. **Navigation found a relationship no single address states.** Recording
   `/map/increment/3/power/8/table` and then `/map/eca/204/3/table`
   returned an `extensional_equivalence` observation: same table, both the
   identity on X_3 (C-040). The mathematics is trivial. The mechanism is
   not: equivalence classes of addresses are raw material for naming
   recurring structure without inventing names (Q-013).
5. **Every result is a node.** Following returned links, a seeded 23-step
   walk from `/map/eca/110/6` visits several kinds and ends at an address
   that alone re-resolves to the same deterministic hash (test). Every link
   returned from 7 roots resolves, or is refused with a reason (test).
6. **Effect ≠ epistemic status.** A bit flip is a *pure* function of the
   address (`effects: pure`), and it is also a *simulated intervention on a
   model* (`epistemic_status`). The registry keeps both fields; collapsing
   them would mislabel one.
7. **Rerun is comparison.** Recording the same address twice gave
   `verdict: reproduced, changed: []` (output, operation versions, code
   hash, environment, materialization). Wall-clock time is reported and
   excluded. This matches the ledger's definition of *reproduced*.
8. **The experiments are undisturbed.** A dry `run_all` gives the 7
   registered run ids; all 58 tests pass; `tools.validate` reports 0
   violations.

Example (real output, abridged):

```
$ curl -s localhost:8765/map/eca/110/6/state/1
{ "protocol": "substrate-purl/0 (provisional)", "kind": "state", "purl": "/map/eca/110/6/state/1",
  "value": {"x": 1, "bits_msb_first": "000001", "popcount": 1, "n_bits": 6, "dynamics": {"family": "eca", "rule": 110, "n": 6}},
  "identity": {"address": "/map/eca/110/6/state/1", "value_sha256": "sha256:22e44e…"},
  "derivation": [{"purl": "/map/eca/110/6", "operation": "substrate.map.eca", …}, {"purl": "/map/eca/110/6/state/1", …}],
  "execution": {"operations": [{"id": "substrate.map.eca", "version": "sha256:…"}, …], "materialized": [], "effects": ["pure"],
                "deterministic_sha256": "sha256:…", "wall_ns": {…, "note": "…excluded from every hash"}},
  "operations": [{"id": "substrate.state.next", "template": "/map/eca/110/6/state/1/next", "executable_here": true, …}, …],
  "next": [{"rel": "transition", "purl": "/map/eca/110/6/state/1/next", "why": "f(x) = 3"},
           {"rel": "trace", "purl": "/map/eca/110/6/state/1/orbit"}, …],
  "links": {"parent": "/map/eca/110/6", "operations": "/operations", "environment": "/environment",
            "executions": "/executions?purl=/map/eca/110/6/state/1"} }

$ curl -s localhost:8765/map/eca/110/6/state/1/orbit/at/5/flip/2/damage/16     # a 6-operation derivation
  → comparison.class = "amplified", distance = [1, 2, 2, 4, 2, 2, 4, 2, …]
$ curl -s localhost:8765/map/eca/90/8/state/5/flip/0/damage/16
  → comparison.class = "recovered", recovery_time = 4
$ curl -s -X POST localhost:8765/map/eca/204/3/table                             # recorded; rerun → "reproduced"
```

## RESULT: answers to the brief's ten questions

| # | Question | Answer from the implementation |
|---|---|---|
| 1 | Existing objects usable as addressable objects? | StateSpace, DeterministicMap (all families), states, Trace, functional-graph analysis and its cycles, projection/congruence summaries, Intervention + damage comparison. All reused, none duplicated. |
| 2 | Smallest PURL abstraction? | A derivation path (ground term): `root/params` then `op/params`, dispatched on kind. |
| 3 | Smallest operation registry? | `Operation(id, segment, applies_to, yields, params, effects, determinism, requires, materializes, epistemic_status, impl, uses)`; its version is the hash of the implementing sources. |
| 4 | Smallest result envelope? | `protocol, kind, purl, value, identity, derivation, execution, operations, next, links`. |
| 5 | Existing provenance machinery? | `artifacts` (canonical JSON, sha256, code_hash, environment, git_state) and the ledger's definition of *reproduced*, reused in a separate store. |
| 6 | Smallest navigable continuation? | The address itself (it encodes its derivation). A content-addressed trail with a parent is needed only for branching (C-039). |
| 7 | Without disturbing the research substrate? | New modules only, plus one leak fix. Nothing writes to `research/registries/` or `runs/`; the store is `.purl-store/` (gitignored). |
| 8 | Tests? | `tests/test_purl.py`: derivation equals instrument output; purity and determinism; known-not-materialized; known-unavailable; error explanations; every next link followable; 23-step walk; GET writes nothing; rerun/compare; equivalence discovery; continuation branching; registry completeness; HTTP. |
| 9 | First curl? | `curl -s localhost:8765/map/eca/90/8/state/5` |
| 10 | First next PURL? | `/map/eca/90/8/state/5/next` → x = 136 |

## INTERPRETATION (INFERRED; not evidence)

* **Two kinds of address.** The PURL/0.1 repository addresses *resources*:
  stateful, event-sourced, authority-bearing, a stored history. These
  addresses name *values*: pure and extensional, where authority is
  irrelevant. The architecture sketch "SubstrateIO → PURL → ACSP" holds
  with that split. Value addresses come from the substrate. Resources (PURL)
  and continuity records (ACSP) can hold and transport value addresses,
  trails and execution records, and none of them needs to implement the
  others.
* **GET must stay pure.** The brief asked for `curl <PURL>` to persist
  provenance. That conflicts with GET safety (PURL/0.1 §3.2, ACSP) and with
  the ledger's discipline. Resolution: GET returns the computed provenance
  in the response; POST to the same address records it. `curl` alone still
  gives the whole computational response.
* **Not built, on evidence rather than preference:**
  * **WASM, LLVM ORC, Tree-sitter, Arrow, NumPy/SciPy/NetworkX kernels.**
    Nothing in this slice needed them. The repository is standard library
    only. The `requires` + `/environment` mechanism is how they would
    enter: as declared, observable, possibly-unavailable operations.
  * **The effect taxonomy.** It is a field, but every registered operation
    is `pure`, so a taxonomy cannot be evidenced yet. The first effectful
    operation is the test of it.
  * **Partial evaluation.** `power/{k}` is the only specialization so far.

## EPISTEMIC STATUS

Everything above is COMPUTATIONAL: execution of the substrate's own models,
where the models are the subject. Bit flips remain SIMULATED interventions.
The equivalence found in observation 4 is an established fact of arithmetic
(3 + 8 ≡ 3 mod 8) observed by the instrument; it is not a discovery.

## ONTOLOGY CHANGE

None. Every addressable kind is an O-1 object; addresses are a
representation of derivations (C-037), at the meta level.

## NEXT QUESTION

Q-013: over the address space, how do extensional equivalence classes grow
with path length, and does recorded navigation find them faster than
enumeration? Pre-register it with a falsification condition before running.
