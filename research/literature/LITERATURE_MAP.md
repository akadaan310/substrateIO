# Literature Map: where the investigation meets established theory

Purpose: for each proposed notion, name the established field, say what the
field already provides, and mark **where (if anywhere) this investigation
begins to differ**. Evidence ids refer to `registries/evidence_sources.json`.
Entries with `verified_in_session: no` are from agent background knowledge and
are queued for verification (Q-011).

| Proposed notion | Established fields / terms | What the field already gives | Where we might differ (status) |
|---|---|---|---|
| bare state, alphabet, state space | automata, symbolic dynamics, dynamical systems | everything | none (ESTABLISHED) |
| bare transition vs recorded event | LTS (LIT-014); event structures (Winskel); provenance (LIT-015) | transitions; causal and conflict relations on events | only the insistence that a *record* differs from the transition it records. That is a methodological rule, not new theory |
| trace | trace semantics; orbit segment | trace equivalence, trace languages | none |
| CTG | functional graph (LIT-003), LTS, Kripke structure, temporal graph | cycles, basins, transients, model checking | no distinct object found (INT-002, H-007 UNRESOLVED) |
| transition language (binary) | sliding-block codes, edge presentation (LIT-012); difference sequences | factor codes, conjugacy, entropy invariance | none for information (H-002 DISPROVEN). Markov-order redistribution (H-012, DISC-001) is probably a hidden-Markov fact |
| transition representation (IR) | compiler IRs (SSA, CFG), abstract interpretation, trace abstraction | a mature theory of abstraction and projection of executions | unclear (OP-009) |
| minimum surviving information | Moore minimisation, Myhill–Nerode, bisimulation, lumpability (LIT-008/009) | the coarsest congruence relative to an observable | none. Collapsed to established theory (H-006 ESTABLISHED) |
| projection, information loss | information theory (LIT-010); abstraction functions | H(X \| P(X)), kernels, factor maps | none; our contribution is systematic application across layers |
| cross-layer equivalence | trace equivalence, (bi)simulation, observational equivalence (LIT-014) | a lattice of equivalences | none. Every "same" must name one (C-030) |
| perturbation propagation | damage spreading (LIT-013); Boolean derivatives; CA Lyapunov exponents; fault injection | spreading metrics, phase transitions | metric naming needs care (F-002) |
| masking / attenuation | dependability (LIT-002); ACE/AVF (LIT-011); coding theory (LIT-007) | fault → error → failure; derating by observability | the link "exact masking ⇔ non-injectivity along the path" (H-004 DERIVED) is elementary and probably folklore |
| cross-layer amplification | fault-propagation analysis; sensitivity analysis; chaos | per-domain metrics | non-monotonicity across layers (H-013, DISC-005). Status in the literature unsearched |
| anomaly | residuals (statistics), fault/error (dependability), model violation (runtime verification) | several incompatible definitions | UNRESOLVED (OP-003) |
| structural lifting / meta-substrate | graph rewriting; category theory (functors, natural transformations); higher-order functions | a formal home for "transformations of transformations" | untested (H-008). Most likely to collapse into category theory |
| substrate descent | stepwise refinement, compiler lowering | refinement calculi | aim differs (inspection rather than implementation). Methodological only |
| seven-stage stratification | abstraction hierarchies (hardware/software stack), compiler pipelines, Marr's levels | many hierarchies with different counts | no evidence yet for seven (H-003 UNRESOLVED) |
| temporal structure | Lamport clocks; point processes; temporal logic (LTL/CTL) | ordering vs causality; rates; interval statistics | synchronous models make most metrics degenerate (OP-004) |
| provenance of research | W3C PROV (LIT-015); workflow provenance | entities, activities, derivations | applying the object-level graph machinery to the research record (H-015). Observation only |

## Fields surveyed but not yet used experimentally

Denotational semantics, process algebra (CSP/CCS/π), temporal logic and model
checking, microarchitecture and micro-operations, formal verification, and
causal inference (interventions and do-calculus: our interventions are
recorded, but no causal *identification* has been attempted).
