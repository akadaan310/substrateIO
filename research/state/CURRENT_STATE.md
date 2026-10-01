# Current Research State: R2 (2026-09-26)

Machine-readable twin: `current_state.json`. Lineage: `registries/research_states.jsonl` (R0 → R1 → R2).

## Research question
When computation is observed as state transitions across multiple
representational spaces, what structure exists in the transformations between
those spaces? Can that structure itself become an object of computation,
measurement, verification and discovery? **Status: open.**

## Current ontology: O-1 (PROVISIONAL)
- **Object level:** Representation, Dynamics, typed Maps (encoding, decoding,
  abstraction/projection, observation, state perturbation, structural
  perturbation, refinement, compilation), and Observation.
- **Meta level:** Epistemic, Nomenclature, and Provenance & Continuity.
- **Meta-Substrate:** an open problem, not a substrate.
- **The seven-stage ladder:** kept as a hypothesis (H-003). The working
  picture has ≥3 orthogonal axes.

See `research/ONTOLOGY.md`.

## Current nomenclature
There are 36 concepts in `registries/nomenclature.json`. Key mappings:
- CTG → annotated LTS or functional graph (an internal alias).
- Transition language over {0,1} → the XOR sliding-block code.
- Minimum surviving information → the coarsest congruence (Moore
  minimisation or a bisimulation quotient).
- Perturbation propagation → damage spreading.
- Observable-relative masking → ACE/AVF.
- "Velocity/acceleration" of computation → REJECTED term.

## Established or derived knowledge used here
- **DERIVED**
  - DRV-001: injective dynamics never mask a state perturbation.
  - DRV-002: rule 90 annihilates single-site damage at t = n/2 on 2^k rings.
  - DRV-003: an edge rewire affects only the ancestor set of the rewired vertex.
  - DRV-004: XOR recoding loses exactly 1 bit.
  - DRV-005: a syndrome locates errors only under the single-error model.
  - DRV-006: history carries information beyond the current state ⇔ the
    process is non-Markov in that representation.
  - DRV-007: a dynamics-compatible projection ⇔ a congruence.
  - DRV-008: integer finite differences on {0,1} add no information.
- **ESTABLISHED (adopted):** H-006. The minimum retained information is
  property-relative, and equals the coarsest congruence for the observable.

## Hypotheses (status after R2)
| id | short | status |
|---|---|---|
| H-001 | history predicts beyond the current state (universal) | **DISPROVEN** → collapses to Markov order |
| H-002 | transitions carry information states lack | **DISPROVEN** (information form); model-order form → H-012 |
| H-003 | natural seven-stage stratification | UNRESOLVED (untested) |
| H-004 | exact masking requires non-injectivity | DERIVED (+ simulated corroboration; not sufficient) |
| H-005 | code-dependent attenuation at the architectural layer | EXPERIMENTALLY_SUPPORTED (model only) |
| H-006 | minimum surviving information is property-relative | ESTABLISHED (collapse to known theory) |
| H-007 | CTG is a distinct object | UNRESOLVED (no evidence of distinctness) |
| H-008 | structural lifting yields new information | UNRESOLVED (untested) |
| H-010 | rewire effect bounded by ancestors; dominated by cycles | SIMULATED (bound DERIVED; dominance lacked a threshold) |
| H-011 | detection ≠ cause identification | DERIVED |
| H-012 | Markov order can drop under transition recoding | EXPERIMENTALLY_SUPPORTED (model only) |
| H-013 | distance non-monotone across layers | EXPERIMENTALLY_SUPPORTED (model only) |
| H-014 | logical masking is observable-relative | SIMULATED (post-hoc; rediscovers ACE) |
| H-015 | research loop = cyclic identifier graph, acyclic versioned trace | OBSERVED (repository; largely by construction) |

## Completed experiments
All experiments ran twice, reproduced with identical hashes, and passed every
check (43/43).

| id | question | key result |
|---|---|---|
| EXP-A | the four one-bit maps | identity/not lose 0 bits; the constant maps lose 1 bit per step; an identity event records a step that a bare transition cannot |
| EXP-B | one-bit traces; predictive history | CMI: iid 1.7e-5, state-Markov 9.9e-6, transition-Markov 0.365 bits (bias bound 2.5e-4) |
| EXP-C | multi-bit functional graphs + calibration | Flajolet–Odlyzko calibration: cyclic nodes −6.3%, tail −0.15%; injective ⇒ no transients |
| EXP-D | single-bit damage in ECA (16-ring) | no masking under injective rules; rule 90 recovers at exactly k = 8 (192/192) |
| EXP-E | single-edge rewires | ancestor bound holds in 1280/1280 rewires; on-cycle effects ≫ off-cycle |
| EXP-F | projections and information loss | minimum retained states 2…256 depending on the observable; XOR recoding fibers all of size 2 |
| EXP-G | simulated cross-layer injection | SEC/SECDED correct 100% of single flips; Hamming location wrong for 100% of double flips; 1413/2880 flips non-monotone across layers |

## Important results (in plain words)
1. The two most "premise-flavoured" hypotheses, H-001 and H-002, did not
   survive in their strong form. Transitions contain no information that
   states lack. They **redistribute** where memory sits in time (H-012,
   DISC-001).
2. The charter's boxed question ("minimum information that must survive") has
   a precise, **already established** answer, but only relative to a chosen
   observable.
3. Masking, information loss and "sameness" are always relative to a map or
   an observable (INT-003). This is the most consistent thread across
   EXP-D, EXP-F and EXP-G.
4. The same machinery applied to the research record behaves as expected. The
   research loop is a cycle over identifiers and a trace over versions.

## Failed hypotheses, contradictions, rejected metrics
- **Failed hypotheses:** F-005 (H-001), F-006 (H-002).
- **Weak tests:** F-001 (B6), F-007 (H-010).
- **Rejected metric:** F-002 (spread).
- **Misleading design:** F-003 (checksum output).
- **Invalid model:** F-004 (leading-order components formula).
- **Implementation defects:** F-008.
- **Validator defect:** F-009 ("provenance" matched "proven").
- **Contradictions between runs:** none. No reproducibility failures.

## Open problems
OP-001 … OP-009 (`registries/open_problems.json`). The most important are:
- OP-001: the stratification question;
- OP-002: lifting;
- OP-004: temporal structure needs asynchronous models;
- OP-005: the hardware boundary;
- OP-006: cross-layer distance.

## Current implementation
- **Language and dependencies:** Python 3.11, standard library only.
- **`substrate/`:** the instruments.
- **`experiments/`:** EXP-A…G, each with a SPEC, CONFIG and checks.
- **`runs/`:** content-addressed artifacts with manifests.
- **`tools/validate.py`:** guards, cross-references, artifact hashes and
  provenance acyclicity.
- **`tools/provenance.py`:** the self-application analysis.
- **`tests/`:** 40 tests, including deliberate wrong promotions.

## Next experiments (dependency order: `registries/research_queue.json`)
- Q-001: pre-registered replication of DISC-001.
- Q-002: damage light-cone metrics.
- Q-003: register-machine rung, which leads to Q-004 (fault injection +
  ACE) and then Q-006 (operational seven-question).
- Q-005: structural lifting.
- Q-007: asynchronous temporal model.

## Known limitations
- Every result is about models; nothing physical was observed.
- Models are tiny (≤ 16-bit state, 8-step programs).
- The entropy estimators are plug-in estimators.
- Several citations are unverified (Q-011).
- Post-hoc analyses (B8, G8) are exploratory.
- The layered model's normalised distances are ad hoc (OP-006).
- Wall-clock timings measure the Python interpreter, not the models.

## Addendum: bridge STASIS-2 (2026-10-01)

Instrument and nomenclature only; no hypothesis, experiment or run changed.
Terms C-041..C-053 and queue items Q-014/Q-015 were added on the bridge branch. The
substrate is the observation end of the purl circle (values, typed terms, execution
records, P-ACSP-EV-1). Reconstruction for cross-repository work: PROTOCOL.md section 1a.
