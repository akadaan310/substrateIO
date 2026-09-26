# Research Charter

## Object of study

This repository investigates **computation as transformations of state across
multiple representational spaces**. It pays particular attention to transition
structure, temporal history, perturbation, projection, information loss,
cross-layer propagation, anomalies, and any structures that emerge from those
transformations.

The ultimate question:

> When computation is observed as state transitions across multiple
> representational spaces, what structure exists in the transformations
> between those spaces? And can that structure itself become an object of
> computation, measurement, verification and discovery?

This question is **open**. Nothing here assumes the answer.

## The investigative ladder

The investigation starts from a minimal alphabet Σ = {0,1} and climbs this ladder:

```
state → transition → event → trace → transition system → graph → structure
      → projection → perturbation → cross-layer effect → structural transformation
      → meta-structure
```

This ladder is **a way to investigate, not a claim about how computation is
organised**. Whether any hierarchy is natural, and how many levels it has, is
itself hypothesis H-003.

## Possible outcomes (all are acceptable)

The research may:

- confirm existing theory;
- rediscover established structures;
- refine existing terminology;
- invalidate proposed distinctions;
- find useful combinations of existing theories;
- possibly produce new structures.

No novelty claim is made without evidence and an explicit novelty scope
(`research/registries/epistemic_statuses.json`). When a proposed structure
turns out to be established mathematics, that result is recorded and the
established formalism is adopted.

## Operating loop

```
Observe → Represent → Formalize → Experiment → Measure → Compare → Challenge → Revise
```

It is never `Observe → Assume → Build`. The priorities, in order:

1. epistemic integrity;
2. formalisation;
3. experimental infrastructure;
4. implementation.

## Standing rules

1. Every claim carries an epistemic status. Statuses are defined in
   `registries/epistemic_statuses.json` and enforced by `substrate/epistemic.py`.
2. **Simulation is never observation.** Every perturbation in this repository
   is a simulated state change on a model. It is not a radiation event, a
   physical upset, or naturally occurring. Executing a model yields `SIMULATED`,
   never `OBSERVED`.
3. **Representation is not reality.** An assembly instruction is a notation. A
   digital state is an abstraction over physical behaviour. A model of layers
   is not the hardware.
4. **"Same" always names an equivalence relation**: state equality, trace
   equivalence, bisimulation, equality of an observable, and so on.
5. **A timestamp orders events and a detection reports an inconsistency.**
   Neither establishes a cause.
6. **Negative results are first-class.** Failures, contradictions and rejected
   metrics go in `registries/failures.json` and are never deleted.
7. **"Not computed" is not "does not exist."** Truncation, sampling and
   resource limits are recorded as part of each result.
8. **No hidden ontology changes.** A change to the conceptual model is recorded
   in `registries/ontology_history.jsonl` with the limitation, the
   alternatives, the rationale and the migration.
9. **Post-hoc analyses are labelled post-hoc.** A post-hoc result cannot reach
   `EXPERIMENTALLY_SUPPORTED` until a pre-registered replication succeeds.
10. **Safety and containment.** Everything runs in simulation. Nothing touches
    production systems, external systems or physical hardware. Any future
    emulator, native-code or fault-injection work runs inside containers or
    VMs, or on dedicated authorised hardware.

## The prime directive

> We are not here to confirm the premise. We are here to create the conditions
> under which the premise can survive or fail.
