"""substrate — a minimal, dependency-free laboratory for studying computation
as transformations of state.

Modules (each is an *instrument*, not a theory):

    core        state spaces over Sigma={0,1}^n and deterministic/stochastic maps
    trace       transition events, traces, logical and wall-clock time
    graph       functional graphs (deterministic dynamics) and general digraphs
    perturb     recorded interventions and baseline/perturbed comparison
    projection  maps between representational spaces, fibers, information loss,
                dynamics-compatibility and coarsest congruences
    info        plug-in information-theoretic estimators
    layers      a simulated, layered abstraction boundary (storage code ->
                architectural value -> program trace -> output)
    epistemic   epistemic statuses and promotion guards
    artifacts   canonical JSON, hashing, run manifests
    ledger      registry I/O used by experiments and tools

Nothing in this package observes physical hardware. Every result it produces
about physical systems is SIMULATED by construction (see research/CHARTER.md).
"""

__version__ = "0.1.0"
