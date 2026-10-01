# Instrument report: typed terms, identity decomposition, ACSP event projection, circle bridge

This is not a research phase. No research state is added, and no hypothesis or
discovery status changes. Failures: F-010. Open problem: OP-010. Terms:
C-041…C-046. Queue: Q-014, Q-015.

## BEFORE
R2 plus the computational-address instrument. The bridge directive of
2026-10-01 asked for SubstrateIO to be the observation end of a five-system
circle (SEURL → PURL → ACSP → SubstrateIO), without becoming its application
layer.

## QUESTION
What must the instrument provide so that other systems can (a) name values
without evaluating them, (b) tell value identity from record identity, and
(c) have their transitions measured through a declared projection?

## ACTION
* `substrate/purl.py`: `parse()` → `Term` → `evaluate()`. `resolve` =
  evaluate ∘ parse, with behaviour otherwise unchanged. `GET /term/<addr>` serves
  the term.
* Identity decomposition: address_id, derivation_id (from the Term),
  value_id (canonical value per kind; None if not materialized),
  environment_id, execution hash. F-010 recorded (reproduced before the fix).
* `substrate/acsp_events.py`: projection P-ACSP-EV-1 over the ACSP/0.1
  `event_list` that deployments actually serve. Records go to
  `POST /observations` (append-only, in the instrument store).
* Fixture: the live field-trial resource's events (2026-10-01).

## OBSERVATION
* Before F-010, `/map/increment/3/power/8/table` and `/map/eca/204/3/table`
  (one table) compared as `different_value`. After: `same_value`.
* The live field trial's event list is chain-consistent. 12 transitions:
  create 1, append 3, checkpoint 1, propose 7. Session switches at t = 6, 8,
  9, 10, 11.
* The purl circle used these endpoints end to end against a real ACSP process
  (purl `circle/experiments/e2e/record-2.json` and `record-3.json`, identical
  deterministic hash). A rebuild after resume reported `reproduced` for every step.
* A fresh participant's GET-only prediction of a value_id matched the value_id
  of the build performed later from its hand-off (purl
  `circle/FRESH-AGENT-EXPERIMENT.md`, condition C).

## RESULT
74 tests OK, 0 violations. Experiment run_ids unchanged.

## INTERPRETATION (INFERRED)
Value addresses and records are different things. Mixing them in one hash
(F-010) made the instrument report a false difference. The decomposition
is the C-041 intension/extension distinction. It is not new.

## EPISTEMIC STATUS
Computational and SIMULATED, as before. Measurements of a live service's
records have no status in the vocabulary yet. They are labelled UNRESOLVED
(OP-010, Q-015).

## ONTOLOGY CHANGE
None.

## NEXT QUESTION
Q-015 (status for external-service records), then Q-013 (equivalence classes vs
path length). The circle now produces scroll-level alias candidates
(C-044) to compare against.
