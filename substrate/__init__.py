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
    purl        computational addresses: derivation paths over these objects,
                an operation registry, and a pure resolver (purl_store records)
    acsp        reader/verifier for ACSP transition-history exports (an
                external system under observation; never imported)

Nothing in this package observes physical hardware. Every result it produces
about physical systems is SIMULATED by construction (see research/CHARTER.md).
"""

__version__ = "0.1.0"
