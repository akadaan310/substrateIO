# Research Continuity Protocol

Every research or engineering session, human or agent, starts by rebuilding
state from the repository. The original conversation is not needed and should
not be assumed.

## 1. Reconstruct (read, in order)

| # | Artifact | Answers |
|---|----------|---------|
| 1 | `research/CHARTER.md` | What are we studying, and under which rules? |
| 2 | `research/state/CURRENT_STATE.md` (+ `current_state.json`) | Where are we? |
| 3 | `research/state/HANDOFF.md` (+ `handoff.json`) | What do we know, think, observe and simulate? What should happen next? |
| 4 | `research/ONTOLOGY.md`, `registries/ontology_history.jsonl` | What is the current conceptual model, and why did it change? |
| 5 | `registries/nomenclature.json` | What do the terms mean, and which of them are established? |
| 6 | `registries/hypotheses.json` | What is being tested, and what is its status? |
| 7 | `registries/experiments.json`, `runs/` | What has been run, and was it reproduced? |
| 8 | `registries/evidence.jsonl`, `registries/evidence_sources.json` | What is the evidence and where does it come from? |
| 9 | `registries/failures.json` | What failed? Which metrics were rejected? |
| 10 | `registries/discoveries.json` | Which candidate patterns exist, and at what stage? |
| 11 | `registries/open_problems.json` | What is unknown? |
| 12 | `registries/research_queue.json` | What is next, in dependency order? |
| 13 | `git log --stat -10`, `research/reports/` | What changed recently, and why? |

## 2. Verify the substrate

```bash
python3 -m unittest discover -s tests -t .   # instruments + epistemic guards
python3 -m tools.validate                     # registries, guards, artifact hashes, provenance
```

If validation fails, fix the substrate or record the failure before doing
anything else.

## 3. Act

1. Choose the next action from the research queue. The queue sets execution
   order by dependency, not scientific importance.
2. Record the action before executing it. Update the queue item's status and,
   for a new experiment, write its `SPEC`, including the falsification
   condition, before running it.
3. Execute: `python3 -m experiments.run_all [EXP-X]`. Run twice to record a
   reproduction.
4. Measure and compare. Update `hypotheses.json` by adding a
   `revision_history` entry. Never overwrite the statement or delete a
   revision.
5. Record interpretations separately from measurements. Interpretations go in
   `evidence_sources.json` with `kind: interpretation` and `status: INFERRED`
   at most.
6. Record failures, contradictions and rejected metrics in `failures.json`.
7. Put candidate patterns in `discoveries.json`, starting at stage
   `candidate_pattern`.
8. Record ontology changes as an `OC-*` record in `ontology_history.jsonl`.

## 4. Close the phase

1. Append a research state `R_{i+1}` to `registries/research_states.jsonl`
   (parent, operation, inputs).
2. Write a phase report in `research/reports/` using the fields BEFORE /
   QUESTION / ACTION / OBSERVATION / RESULT / INTERPRETATION / EPISTEMIC STATUS
   / ONTOLOGY CHANGE / NEXT QUESTION.
3. Regenerate provenance with `python3 -m tools.provenance`, then run
   `python3 -m tools.validate`.
4. Update `CURRENT_STATE.md`, `current_state.json`, `HANDOFF.md` and
   `handoff.json`.
5. Commit with a message naming the research state, the motivating evidence
   and the operation. Do not rewrite history.
