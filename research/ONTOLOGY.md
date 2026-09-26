# Ontology (current: O-1, PROVISIONAL)

The machine-readable history is in `registries/ontology_history.jsonl`. This
file explains the current version and maps every earlier name to it.

## O-1

```
OBJECT LEVEL (what is studied)                 META LEVEL (how it is studied)
────────────────────────────────              ─────────────────────────────────
Representation                                 Epistemic
  alphabet, state space, encoding                statuses, hypotheses, evidence,
Dynamics                                         discoveries, failures
  bare transition, event, trace,               Nomenclature
  transition system, functional graph            terms, mappings to literature
Maps (typed; one concept, many kinds)          Provenance & Continuity
  encoding (injective)                           experiments, runs, manifests,
  decoding (partial inverse)                     research states, lineage graph
  abstraction / projection (many-to-one)
  observation (= map + recording + clock)
  state perturbation (intervention on x)
  structural perturbation (intervention on f)
  refinement, compilation
Observation
  what is recorded, by what mechanism,
  at what resolution, with what clock
```

**Meta-Substrate** is not a substrate in O-1. It is open problem OP-002, whether
lifted levels S₀, S₁, S₂, ... carry new information, and hypothesis H-008.

**The seven-stage ladder** (State, Transition, Temporal History, Transition
Topology, Computational Structure, Representation, Meta-Substrate) is kept as
an investigative ladder. Whether it is a natural stratification is hypothesis
H-003 (UNRESOLVED). The provisional working picture is **at least three
orthogonal axes**, not one sequence:

1. **time / history**: state → transition → trace. A trace is an unrolled
   transition system.
2. **representation / abstraction**: maps between spaces, with their kernels
   and congruences.
3. **order of structure**: object → structure (graph) → transformations of
   structures (lifting).

## Mapping of O-0 names (none are deleted)

| O-0 candidate substrate | O-1 location | Why |
|---|---|---|
| Research Substrate | whole repository (meta level) | umbrella |
| Epistemic Substrate | Epistemic | kept |
| Nomenclature Substrate | Nomenclature | kept |
| Representation Substrate | Representation | kept |
| Observation Substrate | Observation (object level) | observation = map + recording mechanism + clock |
| Experiment Substrate | Provenance & Continuity | experiments are recorded activities |
| Evidence Substrate | Epistemic | evidence is typed by kind and domain |
| Provenance Substrate | Provenance & Continuity | kept |
| Transformation Substrate | Maps | one typed concept |
| Perturbation Substrate | Maps (state or structural perturbation) | same formal type as other maps |
| Projection Substrate | Maps (abstraction/projection) | same formal type |
| Discovery Substrate | Epistemic (discovery ledger) | a discovery is a claim at a stage |
| Meta-Substrate | open problem OP-002 | untested |

## Terms that turned out to be established

(Details in `registries/nomenclature.json` and `literature/LITERATURE_MAP.md`.)

- "Transition graph of a deterministic map" is a **functional graph**.
- "CTG" is an annotated LTS or functional graph (INT-002).
- "Transition language" over {0,1} is the XOR 2-block sliding-block code (INT-001).
- "Minimum information that must survive" for an observable is the coarsest
  congruence, which is Moore minimisation or a bisimulation quotient (H-006).
- "Perturbation propagation" in discrete dynamics is **damage spreading**.
- "Masking relative to output" is **ACE / AVF** reasoning (LIT-011).
