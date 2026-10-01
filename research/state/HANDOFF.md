# Handoff to the next session (from R2)

Machine-readable twin: `handoff.json`. The procedure is in `PROTOCOL.md`.
The full picture is in `CURRENT_STATE.md`.

## Instrument changes since R2 (not a research phase)
- 2026-09-27: computational addresses (`research/reports/instrument-computational-addresses.md`).
- 2026-10-01: parse -> typed term -> evaluate, the identity decomposition (F-010 fixed),
  ACSP event projection P-ACSP-EV-1, and terms C-041..C-046
  (`research/reports/instrument-circle-bridge.md`). The instrument is now the observation
  end of the purl "circle" bridge (see purl `circle/CURRENT-STATE.md`). No hypothesis changed.
  New queue items: Q-014 (cross-provider participant), Q-015 (status for external-service records).

## Bridge STASIS-2 (2026-10-01; not a research phase)
- Registry C-047..C-053 (identity kinds, edge vocabulary, stasis, clock domain, cold
  reconstruction; C-052 addressed transition and C-053 recursive program construction are
  HYPOTHESIS). PROTOCOL.md section 1a: bridge sessions fetch every branch first.
- First measurement for C-053 (purl `circle/DOGFOOD-REPORT.md` section 2): closure of programs
  under five transformers is 0.56-0.78 for state-bound programs and 0.0 for a map. Not a
  hypothesis test: no SPEC was pre-registered. Candidate for one.
- The substrate's own artifacts reproduce from committed refs (purl `circle/cold/report-*.json`).

## Quick start
```bash
python3 -m unittest discover -s tests -t .   # expect 74 OK (~55 s)
python3 -m tools.validate                     # expect 0 violations
python3 -m experiments.run_all --dry          # expect all checks pass, same run_ids as registries/experiments.json
```

## WHAT WE KNOW
These are DERIVED or ESTABLISHED, and each comes with an argument or a source:
- Exact masking of a state perturbation requires non-injective dynamics (DRV-001).
- Binary transition recoding loses exactly 1 bit (DRV-004).
- "History beyond the current state is predictive" is equivalent to "the
  process is non-Markov in this representation" (DRV-006).
- The minimum information that must survive between representations is the
  coarsest congruence for a chosen observable (H-006, LIT-008).
- An ECC syndrome locates an error only under its fault model (DRV-005).
- Rule 90 on 2^k rings annihilates single damage at n/2 (DRV-002).

## WHAT WE THINK
These are INFERRED or PROVISIONAL:
- Every cross-layer statement must name its observable (INT-003).
- There is no single linear hierarchy of layers. The working picture has ≥3
  orthogonal axes (INT-004, O-1).
- CTG and "transition language" are aliases of established objects (INT-001,
  INT-002).

## WHAT WE OBSERVED
These are OBSERVED, from the repository only: the provenance graph of this
research has 4 identifier-level cycles (closed research loops) and is acyclic
when versioned (REPO-001). Nothing physical has been observed.

## WHAT WE SIMULATED
These are SIMULATED, about models only:
- EXP-A…G, all reproduced.
- Injected bit flips in `substrate/layers.py` are not SEUs.
- Key numbers are in CURRENT_STATE.md.
- Post-hoc results: DISC-001 (Markov order can rise under recoding), H-014 and
  G8 (masking 0/80/94% by observable).

## WHAT WE DON'T KNOW
- Whether any natural stratification exists, seven or otherwise (H-003).
- Whether structural lifting yields new information (H-008).
- How to represent anomalies (OP-003).
- Which cross-layer distance is appropriate (OP-006).
- Any physical-layer behaviour (OP-005).
- Whether any finding here is novel in the literature. Most are
  rediscoveries, and the rest have not been searched for.

## WHAT FAILED
F-001 … F-009 (`registries/failures.json`):
- two disproven hypotheses;
- two weak tests;
- one rejected metric;
- one misleading design;
- one invalid asymptotic model;
- implementation defects;
- one validator false positive.

## WHAT CHANGED
- R0 → R1: substrate built (commit "R0 -> R1").
- R1 → R2: experiments recorded twice; hypotheses revised (see each
  `revision_history`); failures, discoveries and REPO-001 recorded; validator
  bug F-009 fixed.
- No ontology change after OC-001. The evidence bearing on O-1 is recorded as
  OE-001.

## WHAT SHOULD HAPPEN NEXT
Follow the dependency order in `registries/research_queue.json`:
1. **Q-001:** pre-register and replicate DISC-001 (cheap, and decides
   H-012's converse).
2. **Q-002:** replace the spread metric with light-cone and support-width
   metrics; re-run EXP-D as a new run.
3. **Q-003 → Q-004:** register-machine traces, then exhaustive fault
   injection with ACE-style analysis. This is the next rung of the
   experimental ladder.
4. **Q-005:** first structural-lifting experiment (H-008).
5. **Q-011:** verify unverified citations.
