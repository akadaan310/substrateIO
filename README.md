# substrateIO: a research substrate for computation as state transformation

This repository is a **reproducible research instrument and record**. It is
not an application. It investigates computation as transformations of state
across representational spaces: transitions, histories, projections,
perturbations, information loss and cross-layer effects. It is built to let
that premise **survive or fail**.

- **Start here:** `PROTOCOL.md` (Research Continuity Protocol) →
  `research/state/HANDOFF.md`.
- **Charter:** `research/CHARTER.md`. **Ontology:** `research/ONTOLOGY.md`.
- **Current state:** `research/state/CURRENT_STATE.md` (and `.json`).

```bash
python3 -m unittest discover -s tests -t .   # instruments + epistemic guards
python3 -m experiments.run_all               # run + record EXP-A..G (run twice to reproduce)
python3 -m tools.provenance                  # provenance graph + self-analysis
python3 -m tools.validate                    # guards, references, artifact hashes, lineage
python3 -m tools.snapshot                    # regenerate state/handoff JSON
python3 -m tools.purl_server                 # computational addresses over HTTP (see below)
```

Requirements: Python ≥ 3.11, standard library only.

## Layout

```
substrate/            instruments: core, trace, graph, perturb, projection, info, layers,
                      epistemic (status guards), artifacts (hashing), ledger (runner),
                      purl + purl_store (computational addresses), acsp (ACSP export reader)
experiments/          EXP-A..G: SPEC (question, hypotheses, falsification) + CONFIG + run()
runs/<EXP>/<hash>/    content-addressed outputs: config, deterministic results, checks, manifest
tests/                instrument tests, validation-of-validation, reproducibility
tools/                validate, provenance (self-application), snapshot
research/
  CHARTER.md  ONTOLOGY.md
  registries/         hypotheses, experiments, evidence (.jsonl + sources), nomenclature,
                      epistemic statuses, failures, discoveries, open problems, research queue,
                      research states (R0→R1→R2), ontology history, executions
  literature/         LITERATURE_MAP.md, SEU_STUDY.md
  provenance/         provenance graph + analysis (generated)
  state/              CURRENT_STATE, HANDOFF (md + json)
  reports/            phase reports (state transitions)
```

## Status in one paragraph (R2)

- Seven experiments ran and reproduced. The universal "history is
  predictive" hypothesis and the claim that "transitions carry information
  states lack" were **disproven**.
- The "minimum information that must survive" question collapsed to an
  **established** answer (the coarsest congruence for a chosen observable).
- Masking, loss and sameness turned out to be observable-relative
  throughout.
- The seven-stage stratification, the CTG as a distinct object, and
  structural lifting remain **untested or unresolved**.
- All perturbation results are **SIMULATED**. Nothing physical has been
  observed.

## Computational addresses (provisional)

The substrate's objects can be addressed by their derivation:

```bash
python3 -m tools.purl_server &                                  # stdlib HTTP on :8765
curl -s localhost:8765/map/eca/90/8/state/5                     # a state under ECA rule 90 on X_8
curl -s localhost:8765/map/eca/90/8/state/5/next                # follow a returned link: f(5) = 136
curl -s localhost:8765/map/eca/90/8/state/5/flip/0/damage/16    # perturb, then compare orbits
curl -s localhost:8765/map/eca/30/40/graph                      # 409: known, not materialized (2^40 states)
curl -s -X POST localhost:8765/map/eca/90/8/graph               # record the execution; again → "reproduced"
curl -s localhost:8765/operations                                # the registry (every contract)
```

GET resolves purely and writes nothing; POST records an execution in
`.purl-store/` (gitignored, never in `research/` or `runs/`). Every response
carries its derivation, operation versions, deterministic hash, and `next`
addresses. See `research/reports/instrument-computational-addresses.md` and
nomenclature C-037 to C-040.
