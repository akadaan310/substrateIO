# Instructions for agents working in this repository

This repository is a **research substrate**, not an application. The code in
`substrate/` and `experiments/` is an instrument. The registries in
`research/registries/` are the record.

**Start every session with `PROTOCOL.md`** (the Research Continuity Protocol).
Read `research/state/HANDOFF.md` first for the short version.

Rules that are easy to break by accident:

- Executing a model produces `SIMULATED` results, never `OBSERVED`. Injected bit
  flips are not SEUs.
- Never change a hypothesis status without adding a `revision_history` entry
  that cites evidence ids. Then run `python3 -m tools.validate`.
- Never edit files under `runs/`. They are content-addressed and hash-checked.
- Post-hoc checks must be listed in the experiment SPEC's `post_hoc_checks`.
- Prefer established terms (see `research/registries/nomenclature.json`).
  Introduce a new term only with a nomenclature entry and a reason.
- Use only the Python 3.11 standard library, unless a dependency is justified
  and recorded.
- Tests: `python3 -m unittest discover -s tests -t .`
