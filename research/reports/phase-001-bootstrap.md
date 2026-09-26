# Phase report 001: bootstrap (R0 → R1 → R2), 2026-09-26

**BEFORE (R0).** Empty repository: no commits, files, terminology,
experiments or dependencies. Python 3.11 was available, with no scientific
packages.

**QUESTION.** Can a reproducible substrate be built that:
1. separates observation, simulation, derivation and interpretation;
2. runs the first experimental ladder (A–G);
3. produces evidence strong enough to move hypotheses in either direction?

**ACTION.**
- **R1:** built the instruments in `substrate/`, with standard-library code
  only, so there are no external dependencies to drift. Also built:
  - epistemic guards and 39 tests, including deliberate wrong promotions;
  - the registries;
  - ontology O-1 (OC-001 merged 13 candidate substrates into an object/meta
    split with typed maps);
  - experiments A–G, each with a falsification condition written before
    execution.
- **R2:** executed every experiment twice on committed code. Revised the
  hypotheses from the evidence. Recorded failures and discovery candidates.
  Ran the provenance self-analysis.

**OBSERVATION.**
- 43/43 checks passed. All 7 runs reproduced with identical deterministic
  hashes.
- Two checks are post-hoc and labelled as such: B8 (Markov order rising
  under recoding) and G8 (masking relative to the observable).
- Tampering with a recorded artifact was detected by `tools/validate.py`
  (manual demonstration: the altered file was restored and validation
  returned to 0 violations).
- The validator itself had a false positive (F-009).

**RESULT.**
- **Disproven:** H-001 (universal predictive history) and H-002
  (information form).
- **Collapsed to established theory:** H-006, the minimum surviving
  information, is the coarsest congruence.
- **Derived:** H-004 (masking requires non-injectivity) and H-011 (detection
  ≠ attribution).
- **Model-scope EXPERIMENTALLY_SUPPORTED:** H-005, H-012 and H-013.
- **Untested:** H-003 (seven), H-007 (CTG), H-008 (lifting).

**INTERPRETATION** (INFERRED, INT-001…004):
- The premise that "transitions are a richer primitive than states" does
  not survive for information content.
- What survives, weakly, is the claim that the choice of representation
  moves memory across time, and that every cross-layer notion (masking,
  loss, sameness) is relative to an observable.
- Nothing so far requires new mathematics.

**EPISTEMIC STATUS.** Everything above is about models or about the
repository. No physical claim was made beyond LITERATURE_SUPPORTED.

**ONTOLOGY CHANGE.** OC-001 (O-0 → O-1) at R1. At R2 the evidence was
consistent with O-1 (OE-001), so no change was made.

**NEXT QUESTION.** Do the model-scope results survive at the next rung, a
register machine with instruction traces (Q-003/Q-004)? And does the
seven-stage question admit an operational test there (Q-006)?
