"""Computational addresses (PURL, provisional): the substrate's objects made addressable.

A PURL here is a **derivation path**: a root constructor followed by
operations, each applied to the object the prefix denotes.

    /map/eca/90/8                      the map  f = ECA rule 90 on X_8
    /map/eca/90/8/state/5              the state x = 5 under f
    /map/eca/90/8/state/5/next         the state f(5)
    /map/eca/90/8/state/5/flip/0       the state 5 XOR 1 (a recorded, SIMULATED intervention)
    /map/eca/90/8/state/5/flip/0/damage/16
                                       baseline vs perturbed orbit, compared (perturb.py)
    /map/eca/90/8/graph                the functional graph (graph.py)
    /map/increment/3/power/8           the map f^8, a derived map

The address is not a pointer *to* a computer: it is a coordinate *in* the
space of computational objects this repository already defines (core, trace,
graph, projection, perturb). Nothing here is a new ontology; each kind below
is an existing O-1 object:

    space        StateSpace X_n                        (Representation)
    state        x in X_n, optionally under a map f     (Representation / Dynamics)
    map          DeterministicMap f : X_n -> X_n        (Maps)
    trace        Trace (logical time only)              (Dynamics)
    graph        functional graph of f                  (Dynamics)
    cycle        one attractor of f                     (Dynamics)
    projection   observable O with ker O vs f           (Maps: abstraction/projection)
    damage       baseline/perturbed comparison          (Maps: state perturbation)

Principles carried over from the charter:

* Resolution is PURE: an address always denotes the same value (extensional).
  Wall-clock time is reported separately and never hashed.
* "Not computed" is not "does not exist" (charter rule 7): an object can be
  KNOWN (well-formed address) without being MATERIALIZED (e.g. a 2^40 table).
  Refusals say which, and why.
* "Same" names an equivalence (rule 4): two addresses can denote one table.
  `identity.table_sha256` is extensional identity; the address is not.
* Operations are looked up in a registry, never evaluated. Each declares its
  effects, determinism, requirements and implementation.

Standard library only. An operation may *declare* an optional dependency
(e.g. numpy); if it is absent the operation is KNOWN but UNAVAILABLE here.
"""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import platform
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from . import artifacts as A
from .core import StateSpace, eca, eca_step, hamming, increment, popcount, random_map, random_permutation
from .graph import functional_graph_analysis, public
from .perturb import Intervention, compare_state_sequences
from .projection import congruence_summary, information_loss, to_transitions
from .trace import run, step_states

PROTOCOL = "substrate-purl/0 (provisional)"

LIMITS = {
    "table_states": 1 << 16,   # materialize a lookup table only up to 2^16 states
    "max_bits": 64,            # addressable state spaces (step functions work without a table)
    "trace_steps": 4096,
    "orbit_steps": 1 << 16,
    "power": 1 << 20,
    "links": 16,               # concrete next-links per list
}


class PurlError(Exception):
    """A resolution failure with an HTTP-like status and a machine code."""

    def __init__(self, status: int, code: str, message: str, **details):
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details

    def doc(self, purl: str) -> dict:
        return {"protocol": PROTOCOL, "kind": "error", "purl": purl,
                "error": {"status": self.status, "code": self.code, "message": self.message, **self.details}}


# ---------------------------------------------------------------------------
# Objects
# ---------------------------------------------------------------------------

@dataclass
class MapHandle:
    """A map known by construction. `step` works without a table; `table` is
    the materialized extension, produced only on demand and within limits."""
    n: int
    step: Callable[[int], int]
    make_table: Optional[Callable[[], List[int]]]
    construction: dict
    needs_table_for_step: bool = False
    _table: Optional[List[int]] = None

    def table(self, ctx: "Ctx", why: str) -> List[int]:
        if self._table is not None:
            return self._table
        size = 1 << self.n
        if size > LIMITS["table_states"] or self.make_table is None:
            raise PurlError(409, "not_materialized",
                            "The map is KNOWN but its table is not materialized: {} states exceed the limit {}.".format(size, LIMITS["table_states"]),
                            needed_for=why, states=size, limit=LIMITS["table_states"],
                            note="Not computed is not 'does not exist' (charter rule 7). Operations that need only a step function still work.")
        t0 = time.perf_counter_ns()
        self._table = self.make_table()
        ctx.materialized.append({"object": "table", "states": size, "why": why, "wall_ns": time.perf_counter_ns() - t0})
        return self._table


@dataclass
class Obj:
    kind: str
    purl: str
    value: dict
    map: Optional[MapHandle] = None      # the dynamics this object lives under, if any
    x: Optional[int] = None              # state value, for kind == state
    extra: dict = field(default_factory=dict)


@dataclass
class Ctx:
    steps: List[dict] = field(default_factory=list)
    materialized: List[dict] = field(default_factory=list)
    operations: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# The operation registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Param:
    name: str
    kind: str = "int"             # "int" | "choice"
    minimum: int = 0
    choices: Tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class Operation:
    id: str
    segment: Tuple[str, ...]      # path tokens that select the operation
    applies_to: str               # object kind (or "root")
    yields: str
    params: Tuple[Param, ...]
    description: str
    impl: Callable[..., Obj]
    uses: Tuple[Callable, ...] = ()   # substrate functions the implementation relies on
    effects: str = "pure"
    determinism: str = "deterministic"
    requires: Tuple[str, ...] = ()    # optional modules
    materializes: str = "nothing"     # what, if anything, must be materialized
    epistemic_status: str = "computational"

    def contract(self) -> dict:
        return {
            "id": self.id,
            "segment": "/".join(self.segment),
            "applies_to": self.applies_to,
            "yields": self.yields,
            "params": [{"name": p.name, "type": p.kind, "minimum": p.minimum if p.kind == "int" else None,
                        "choices": list(p.choices) or None, "description": p.description} for p in self.params],
            "template": "/".join(self.segment + tuple("{" + p.name + "}" for p in self.params)),
            "description": self.description,
            "effects": self.effects,
            "determinism": self.determinism,
            "requires": list(self.requires),
            "materializes": self.materializes,
            "epistemic_status": self.epistemic_status,
            "implementation": implementation_refs(self),
        }


REGISTRY: List[Operation] = []


def op(**kw):
    def deco(fn):
        REGISTRY.append(Operation(impl=fn, **kw))
        return fn
    return deco


def _source_digest(fn: Callable) -> Tuple[str, str]:
    src = inspect.getsource(fn)
    path = inspect.getsourcefile(fn) or ""
    return (A.sha256_text(src), __import__("os").path.relpath(path, A.ROOT))


def implementation_refs(o: Operation) -> List[dict]:
    """Context references to the code that implements the operation: surface,
    locator, digest. A reference grants awareness only, not access or execution."""
    out = []
    for fn in (o.impl,) + o.uses:
        digest, path = _source_digest(fn)
        out.append({"surface": "git:substrateIO", "locator": "{}#{}".format(path, fn.__qualname__),
                    "digest": "sha256:" + digest})
    return out


def operation_version(o: Operation) -> str:
    return "sha256:" + A.sha256_obj([r["digest"] for r in implementation_refs(o)])


def missing_requirements(o: Operation) -> List[str]:
    return [m for m in o.requires if importlib.util.find_spec(m) is None]


def operations_for(kind: str) -> List[Operation]:
    return [o for o in REGISTRY if o.applies_to == kind]


# ---------------------------------------------------------------------------
# Constructors (root operations)
# ---------------------------------------------------------------------------

def _check_bits(n: int) -> None:
    if not 1 <= n <= LIMITS["max_bits"]:
        raise PurlError(422, "out_of_range", "n must be in 1..{}".format(LIMITS["max_bits"]), param="n")


def _map_obj(purl: str, h: MapHandle, name: str) -> Obj:
    return Obj("map", purl, {"name": name, "n_bits": h.n, "states": 1 << h.n, "construction": h.construction}, map=h)


@op(id="substrate.space", segment=("space",), applies_to="root", yields="space",
    params=(Param("n", minimum=1, description="number of bits"),),
    description="The state space X_n = {0,1}^n.", uses=(StateSpace,))
def _space(ctx, parent, purl, n):
    _check_bits(n)
    return Obj("space", purl, {"n_bits": n, "states": 1 << n, "alphabet": [0, 1]}, extra={"n": n})


@op(id="substrate.map.eca", segment=("map", "eca"), applies_to="root", yields="map",
    params=(Param("rule", description="Wolfram rule 0..255"), Param("n", minimum=1, description="ring size")),
    description="Elementary cellular automaton on a ring of n cells. Steps are computed without a table (eca_step).",
    uses=(eca, eca_step))
def _map_eca(ctx, parent, purl, rule, n):
    if rule > 255:
        raise PurlError(422, "out_of_range", "rule must be 0..255", param="rule")
    _check_bits(n)
    h = MapHandle(n, lambda x: eca_step(rule, n, x), lambda: eca(rule, n).table, {"family": "eca", "rule": rule, "n": n})
    return _map_obj(purl, h, "eca{}".format(rule))


@op(id="substrate.map.increment", segment=("map", "increment"), applies_to="root", yields="map",
    params=(Param("n", minimum=1),), description="x -> x + 1 mod 2^n. Steps need no table.", uses=(increment,))
def _map_inc(ctx, parent, purl, n):
    _check_bits(n)
    m = (1 << n) - 1
    h = MapHandle(n, lambda x: (x + 1) & m, lambda: increment(n).table, {"family": "increment", "n": n})
    return _map_obj(purl, h, "increment")


def _seeded(kind: str, ctor: Callable):
    def impl(ctx, parent, purl, n, seed):
        _check_bits(n)
        holder: Dict[str, MapHandle] = {}
        h = MapHandle(n, lambda x: holder["h"].table(ctx, "step of a seeded random map")[x], lambda: ctor(n, seed).table,
                      {"family": kind, "n": n, "seed": seed}, needs_table_for_step=True)
        holder["h"] = h
        return _map_obj(purl, h, kind)
    return impl


op(id="substrate.map.random", segment=("map", "random"), applies_to="root", yields="map",
   params=(Param("n", minimum=1), Param("seed")), description="Uniform random mapping (seeded). Every step needs the full table.",
   uses=(random_map,), materializes="table (for any step)")(_seeded("random", random_map))
op(id="substrate.map.permutation", segment=("map", "permutation"), applies_to="root", yields="map",
   params=(Param("n", minimum=1), Param("seed")), description="Uniform random permutation (seeded). Every step needs the full table.",
   uses=(random_permutation,), materializes="table (for any step)")(_seeded("permutation", random_permutation))


# ---------------------------------------------------------------------------
# Operations on objects
# ---------------------------------------------------------------------------

def _state(purl: str, h: Optional[MapHandle], n: int, x: int, **extra) -> Obj:
    sp = StateSpace(n)
    return Obj("state", purl, {"x": x, "bits_msb_first": sp.fmt(x), "popcount": popcount(x), "n_bits": n,
                               "dynamics": h.construction if h else None, **extra}, map=h, x=x)


def _check_state(n: int, x: int) -> None:
    if x >= 1 << n:
        raise PurlError(422, "out_of_range", "x must be < 2^{}".format(n), param="x")


@op(id="substrate.space.state", segment=("state",), applies_to="space", yields="state",
    params=(Param("x"),), description="A state of the space, without dynamics.")
def _space_state(ctx, parent, purl, x):
    _check_state(parent.extra["n"], x)
    return _state(purl, None, parent.extra["n"], x)


@op(id="substrate.map.state", segment=("state",), applies_to="map", yields="state",
    params=(Param("x"),), description="A state of the map's space, under the map's dynamics.")
def _map_state(ctx, parent, purl, x):
    _check_state(parent.map.n, x)
    return _state(purl, parent.map, parent.map.n, x)


def _need_dynamics(o: Obj) -> MapHandle:
    if o.map is None:
        raise PurlError(404, "no_dynamics", "This state has no dynamics. Address it under a map: /map/.../state/{x}.")
    return o.map


@op(id="substrate.state.next", segment=("next",), applies_to="state", yields="state", params=(),
    description="The successor f(x): one transition of the map.")
def _next(ctx, parent, purl):
    h = _need_dynamics(parent)
    y = h.step(parent.x)
    return _state(purl, h, h.n, y, transition={"src": parent.x, "dst": y, "delta_xor": parent.x ^ y})


@op(id="substrate.state.flip", segment=("flip",), applies_to="state", yields="state", params=(Param("bit"),),
    description="State perturbation: x XOR 2^bit. A recorded, SIMULATED intervention on a model, not a physical event.",
    uses=(Intervention,), epistemic_status="simulated intervention on a computational model")
def _flip(ctx, parent, purl, bit):
    n = parent.value["n_bits"]
    if bit >= n:
        raise PurlError(422, "out_of_range", "bit must be < {}".format(n), param="bit")
    iv = Intervention("state_bit_flip", time=None, params={"bit": bit})
    y = iv.state_fn()(parent.x)
    return _state(purl, parent.map, n, y, intervention=iv.record(), perturbed_from=parent.x)


@op(id="substrate.state.trace", segment=("trace",), applies_to="state", yields="trace", params=(Param("steps", minimum=1),),
    description="The trace of `steps` transitions from this state (logical time only).", uses=(run, step_states))
def _trace(ctx, parent, purl, steps):
    h = _need_dynamics(parent)
    if steps > LIMITS["trace_steps"]:
        raise PurlError(422, "out_of_range", "steps must be <= {}".format(LIMITS["trace_steps"]), param="steps")
    tr = run(h.step, h.n, parent.x, steps, clock=False)
    states = step_states(tr)
    return Obj("trace", purl, {"x0": parent.x, "steps": steps, "states": states,
                               "distinct_states": len(set(states))}, map=h, extra={"states": states})


@op(id="substrate.state.orbit", segment=("orbit",), applies_to="state", yields="trace", params=(),
    description="Iterate until a state repeats: transient (tail) + cycle. Needs no table.")
def _orbit(ctx, parent, purl):
    h = _need_dynamics(parent)
    seen: Dict[int, int] = {}
    xs, x = [], parent.x
    while x not in seen:
        if len(xs) >= LIMITS["orbit_steps"]:
            raise PurlError(409, "not_computed", "No repeat within {} steps; the orbit is KNOWN but not computed.".format(LIMITS["orbit_steps"]),
                            steps_tried=len(xs))
        seen[x] = len(xs)
        xs.append(x)
        x = h.step(x)
    mu = seen[x]
    return Obj("trace", purl, {"x0": parent.x, "states": xs, "tail_length": mu, "cycle_length": len(xs) - mu,
                               "cycle_entry": x}, map=h, extra={"states": xs, "cycle_entry": x})


@op(id="substrate.state.damage", segment=("damage",), applies_to="state", yields="damage", params=(Param("horizon", minimum=1),),
    description="Compare the orbit of this (perturbed) state with the orbit of the state it was perturbed from, over `horizon` steps.",
    uses=(compare_state_sequences,), epistemic_status="simulated intervention on a computational model")
def _damage(ctx, parent, purl, horizon):
    h = _need_dynamics(parent)
    base = parent.value.get("perturbed_from")
    if base is None:
        raise PurlError(404, "no_baseline", "damage applies to a perturbed state: /…/state/{x}/flip/{bit}/damage/{horizon}.")
    if horizon > LIMITS["trace_steps"]:
        raise PurlError(422, "out_of_range", "horizon must be <= {}".format(LIMITS["trace_steps"]), param="horizon")
    b = step_states(run(h.step, h.n, base, horizon, clock=False))
    p = step_states(run(h.step, h.n, parent.x, horizon, clock=False))
    injected = [i for i in range(h.n) if (base ^ parent.x) >> i & 1]
    cmp = compare_state_sequences(b, p, 0, h.n, injected)
    return Obj("damage", purl, {"baseline_x0": base, "perturbed_x0": parent.x, "horizon": horizon,
                                "distance": [hamming(u, v) for u, v in zip(b, p)], "comparison": cmp}, map=h)


@op(id="substrate.map.table", segment=("table",), applies_to="map", yields="map", params=(),
    description="Materialize the map: the same map, now with its lookup table (its extension) computed and hashed. "
                "KNOWN -> MATERIALIZED as an explicit, addressable step.", materializes="table")
def _table(ctx, parent, purl):
    t = parent.map.table(ctx, "explicit materialization")
    o = _map_obj(purl, parent.map, parent.value["name"])
    o.value = dict(o.value, table=t if len(t) <= 256 else None, table_omitted=len(t) > 256)
    return o


@op(id="substrate.map.graph", segment=("graph",), applies_to="map", yields="graph", params=(),
    description="The functional graph of f: cycles (attractors), basins, transients, Garden-of-Eden states.",
    uses=(functional_graph_analysis, public), materializes="table")
def _graph(ctx, parent, purl):
    t = parent.map.table(ctx, "functional graph")
    a = functional_graph_analysis(t)
    return Obj("graph", purl, public(a), map=parent.map, extra={"cycles": [sorted(c) for c in a["_cycles"]]})


@op(id="substrate.graph.cycle", segment=("cycle",), applies_to="graph", yields="cycle", params=(Param("k"),),
    description="The k-th attractor (cycle) of the functional graph.")
def _cycle(ctx, parent, purl, k):
    cycles = parent.extra["cycles"]
    if k >= len(cycles):
        raise PurlError(422, "out_of_range", "the graph has {} cycles".format(len(cycles)), param="k")
    return Obj("cycle", purl, {"k": k, "length": len(cycles[k]), "states": cycles[k]}, map=parent.map, extra={"states": cycles[k]})


@op(id="substrate.map.power", segment=("power",), applies_to="map", yields="map", params=(Param("k", minimum=1),),
    description="The derived map f^k (k-fold composition). Steps need no table if f's steps need none.")
def _power(ctx, parent, purl, k):
    if k > LIMITS["power"]:
        raise PurlError(422, "out_of_range", "k must be <= {}".format(LIMITS["power"]), param="k")
    f = parent.map

    def step(x):
        for _ in range(k):
            x = f.step(x)
        return x
    h = MapHandle(f.n, step, (lambda: [step(x) for x in range(1 << f.n)]) if f.make_table else None,
                  {"family": "power", "k": k, "of": f.construction}, needs_table_for_step=f.needs_table_for_step)
    return _map_obj(purl, h, "power")


@op(id="substrate.map.rewire", segment=("rewire",), applies_to="map", yields="map", params=(Param("src"), Param("dst")),
    description="Structural perturbation: the map equal to f except f(src) = dst. A SIMULATED intervention on f.",
    uses=(Intervention,), materializes="table", epistemic_status="simulated intervention on a computational model")
def _rewire(ctx, parent, purl, src, dst):
    f = parent.map
    for name, v in (("src", src), ("dst", dst)):
        _check_state(f.n, v)
    t = Intervention("edge_rewire", params={"src": src, "new_dst": dst}).apply_to_table(f.table(ctx, "structural perturbation"))
    h = MapHandle(f.n, lambda x: t[x], lambda: t, {"family": "rewire", "src": src, "dst": dst, "of": f.construction})
    h._table = t
    return _map_obj(purl, h, "rewire")


OBSERVABLES = {"popcount": popcount, "parity": lambda x: popcount(x) & 1, "bit0": lambda x: x & 1}


@op(id="substrate.map.project", segment=("project",), applies_to="map", yields="projection",
    params=(Param("observable", kind="choice", choices=tuple(OBSERVABLES)),),
    description="Project X_n through an observable O: information lost, and the coarsest congruence of f refining ker O.",
    uses=(information_loss, congruence_summary), materializes="table")
def _project(ctx, parent, purl, observable):
    t = parent.map.table(ctx, "projection")
    O = OBSERVABLES[observable]
    return Obj("projection", purl, {"observable": observable,
                                    "information_loss": information_loss(range(len(t)), O),
                                    "congruence": congruence_summary(t, O)}, map=parent.map)


@op(id="substrate.trace.transitions", segment=("transitions",), applies_to="trace", yields="trace", params=(),
    description="Change of representation: states -> XOR transitions d_t = x_t XOR x_{t+1}.", uses=(to_transitions,))
def _transitions(ctx, parent, purl):
    d = to_transitions(parent.extra["states"])
    return Obj("trace", purl, {"representation": "transitions (XOR)", "deltas": d}, map=parent.map, extra={"states": parent.extra["states"]})


@op(id="substrate.trace.at", segment=("at",), applies_to="trace", yields="state", params=(Param("t"),),
    description="The state at logical time t of the trace.")
def _trace_at(ctx, parent, purl, t):
    states = parent.extra["states"]
    if t >= len(states):
        raise PurlError(422, "out_of_range", "t must be < {}".format(len(states)), param="t")
    return _state(purl, parent.map, parent.map.n, states[t])


@op(id="numpy.map.spectrum", segment=("spectrum",), applies_to="map", yields="spectrum", params=(),
    description="Eigenvalues of the 0/1 transition matrix of f (numpy.linalg.eigvals).", requires=("numpy",),
    materializes="table and a 2^n x 2^n matrix")
def _spectrum(ctx, parent, purl):
    import numpy as np  # declared requirement; only reached when present
    t = parent.map.table(ctx, "transition matrix")
    m = np.zeros((len(t), len(t)))
    for x, y in enumerate(t):
        m[y, x] = 1.0
    ev = np.linalg.eigvals(m)
    return Obj("spectrum", purl, {"eigenvalues": sorted([[round(float(z.real), 12), round(float(z.imag), 12)] for z in ev])}, map=parent.map)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------

def _tokens(purl: str) -> List[str]:
    p = purl.split("?", 1)[0].strip("/")
    return [t for t in p.split("/") if t]


def _param(p: Param, tok: str) -> Any:
    if p.kind == "choice":
        if tok not in p.choices:
            raise PurlError(422, "invalid_param", "{} must be one of {}".format(p.name, list(p.choices)), param=p.name)
        return tok
    if not tok.isdigit():
        raise PurlError(400, "malformed", "{} must be a non-negative integer, got {!r}".format(p.name, tok), param=p.name)
    v = int(tok)
    if v < p.minimum:
        raise PurlError(422, "out_of_range", "{} must be >= {}".format(p.name, p.minimum), param=p.name)
    return v


def canonical(purl: str) -> str:
    return "/" + "/".join(_tokens(purl))


# ---------------------------------------------------------------------------
# Typed terms: parse (no evaluation) -> Term -> evaluate
#
# A Term is the ground term an address denotes (C-037), checked against the
# many-sorted signature the registry declares (applies_to -> yields) WITHOUT
# running any operation. This stage exists because derivation_id must be
# computable before, and independently of, evaluation. Parse checks syntax and
# sorts (kinds) and parameter types; constraints that depend on other
# parameters' values (x < 2^n, bit < n) remain evaluation errors.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Step:
    op: str                       # operation id
    args: Tuple[Any, ...]
    prefix: str                   # the address of the sub-term ending here
    applies_to: str
    yields: str


@dataclass(frozen=True)
class Term:
    address: str                  # canonical address
    steps: Tuple[Step, ...]

    @property
    def kind(self) -> str:
        return self.steps[-1].yields

    def doc(self) -> dict:
        return {"address": self.address, "kind": self.kind,
                "steps": [{"op": s.op, "args": list(s.args), "sort": "{} -> {}".format(s.applies_to, s.yields),
                           "prefix": s.prefix} for s in self.steps],
                "requires": sorted({m for s in self.steps for m in _by_id(s.op).requires}),
                "derivation_id": derivation_id(self)}


def parse(purl: str) -> Term:
    """Address -> typed term. Pure, evaluates nothing. Raises PurlError (400/404/422) on ill-formed or ill-sorted input."""
    toks = _tokens(purl)
    if not toks:
        raise PurlError(400, "empty", "Empty address. Start at /map/... or /space/...; see /operations.")
    kind, at, i, steps = "root", "/", 0, []
    while i < len(toks):
        cands = [o for o in operations_for(kind) if tuple(toks[i:i + len(o.segment)]) == o.segment]
        if not cands:
            raise PurlError(404, "unknown_operation", "No operation {!r} applies to a {}.".format(toks[i], kind),
                            at=at, applicable=[o.contract()["template"] for o in operations_for(kind)])
        o = max(cands, key=lambda c: len(c.segment))
        j = i + len(o.segment)
        if len(toks) < j + len(o.params):
            raise PurlError(400, "missing_params", "{} needs {}".format(o.id, [p.name for p in o.params]), operation=o.id)
        args = tuple(_param(p, t) for p, t in zip(o.params, toks[j:j + len(o.params)]))
        at = "/" + "/".join(toks[:j + len(o.params)])
        steps.append(Step(o.id, args, at, o.applies_to, o.yields))
        kind, i = o.yields, j + len(o.params)
    return Term(at, tuple(steps))


def evaluate(term: Term, ctx: Optional[Ctx] = None) -> Tuple[Obj, Ctx]:
    """Typed term -> value. Checks executability of every step before running any."""
    ctx = ctx or Ctx()
    for s in term.steps:
        o = _by_id(s.op)
        miss = missing_requirements(o)
        if miss:
            raise PurlError(501, "unavailable_here", "Operation {} is KNOWN and described, but not executable in this environment.".format(o.id),
                            operation=o.contract(), missing=miss)
    cur = Obj("root", "", {})
    for s in term.steps:
        o = _by_id(s.op)
        t0 = time.perf_counter_ns()
        cur = o.impl(ctx, cur, s.prefix, *s.args)
        ctx.steps.append({"purl": s.prefix, "operation": o.id, "kind": cur.kind, "wall_ns": time.perf_counter_ns() - t0})
        ctx.operations.append(o.id)
    return cur, ctx


def resolve(purl: str, ctx: Optional[Ctx] = None) -> Tuple[Obj, Ctx]:
    """parse then evaluate. Raises PurlError on any failure."""
    return evaluate(parse(purl), ctx)


# ---------------------------------------------------------------------------
# Identity decomposition. One hash per thing that can independently be "the
# same"; none of them is folded into another.
#
#   address_id      H(canonical address)
#   derivation_id   H([(operation, operation version, args)])   (needs only the Term)
#   value_id        H(kind, canonical value of that kind)        (extensional; None if not materialized)
#   environment_id  H(observed capabilities)
#   execution_id    H(derivation, environment, occurrence)       (assigned only when an execution is recorded)
#
# Semantic equivalence beyond equal canonical values gets no id: it stays a
# recorded observation with evidence.
# ---------------------------------------------------------------------------

def _h(obj: Any) -> str:
    return "sha256:" + A.sha256_obj(obj)


def address_id(purl: str) -> str:
    return _h({"address": canonical(purl)})


def derivation_id(term: Term) -> str:
    return _h([[s.op, operation_version(_by_id(s.op)), list(s.args)] for s in term.steps])


def canonical_value(o: Obj) -> Tuple[Optional[Any], str]:
    """The value of an object *as its kind*, stripped of how it was reached. Returns (value, rule)."""
    if o.kind == "map":
        if o.map._table is None:
            return None, "a map's canonical value is its table (extension); not materialized here"
        return {"n": o.map.n, "table": o.map._table}, "table (extensional equality, C-040)"
    if o.kind == "state":
        return {"n": o.value["n_bits"], "x": o.value["x"]}, "(n, x); dynamics and provenance are context, not value"
    if o.kind == "space":
        return {"n": o.value["n_bits"]}, "n"
    if o.kind == "trace" and "states" in o.value:
        return {"n": o.map.n if o.map else None, "states": o.value["states"]}, "(n, state sequence)"
    if o.kind == "cycle":
        return {"n": o.map.n, "states": sorted(o.value["states"])}, "(n, set of states)"
    return o.value, "the full value document (no coarser canonical form declared for this kind)"


def value_id(o: Obj) -> Optional[str]:
    v, _ = canonical_value(o)
    return None if v is None else _h({"kind": o.kind, "value": v})


def environment_id(env: Optional[dict] = None) -> str:
    env = env or environment()
    return _h({k: env[k] for k in ("runtime", "python", "implementation", "modules")})


# ---------------------------------------------------------------------------
# Envelope: the self-describing, navigable response
# ---------------------------------------------------------------------------

def _link(purl: str, rel: str, why: str = "") -> dict:
    d = {"rel": rel, "purl": purl}
    if why:
        d["why"] = why
    return d


def next_links(o: Obj) -> List[dict]:
    """Concrete addresses one step away. Every one resolves (or is refused with a reason)."""
    L, p, n = [], o.purl, LIMITS["links"]
    if o.kind == "map":
        L += [_link(p + "/state/0", "state"), _link(p + "/power/2", "derive", "f∘f")]
        if not (o.map.make_table and (1 << o.map.n) <= LIMITS["table_states"]):
            L.append(_link(p + "/graph", "graph", "KNOWN; refused here: table not materializable"))
        else:
            L += [_link(p + "/graph", "graph"), _link(p + "/project/popcount", "projection"),
                  _link(p + "/rewire/0/0", "perturb", "structural perturbation")]
        L.append(_link(p + "/spectrum", "analysis", "requires numpy"))
    elif o.kind == "space":
        L += [_link(p + "/state/{}".format(x), "state") for x in range(min(o.value["states"], 4))]
    elif o.kind == "state":
        if o.map is not None:
            cheap = not o.map.needs_table_for_step or o.map._table is not None  # never materialize just to suggest a link
            L += [_link(p + "/next", "transition", "f(x) = {}".format(o.map.step(o.x)) if cheap else ""),
                  _link(p + "/orbit", "trace"), _link(p + "/trace/8", "trace")]
            if "perturbed_from" in o.value:
                L.append(_link(p + "/damage/16", "compare", "baseline vs perturbed orbit"))
        L += [_link(p + "/flip/{}".format(b), "perturb") for b in range(min(o.value["n_bits"], 4))]
    elif o.kind == "trace":
        L.append(_link(p + "/transitions", "representation"))
        L += [_link(p + "/at/{}".format(t), "state") for t in range(min(len(o.extra["states"]), n))]
    elif o.kind == "graph":
        L += [_link(p + "/cycle/{}".format(k), "cycle") for k in range(min(len(o.extra["cycles"]), n))]
    elif o.kind == "cycle":
        root = p.rsplit("/graph/", 1)[0]
        L += [_link(root + "/state/{}".format(x), "state") for x in o.extra["states"][:n]]
    elif o.kind in ("projection", "damage", "spectrum"):
        L.append(_link(p.rsplit("/", 2 if o.kind != "spectrum" else 1)[0], "up"))
    return L


def identity(o: Obj, term: Optional[Term] = None) -> dict:
    term = term or parse(o.purl)
    v, rule = canonical_value(o)
    out = {"address": o.purl, "value_sha256": "sha256:" + A.sha256_obj(o.value),
           "address_id": address_id(o.purl), "derivation_id": derivation_id(term),
           "value_id": value_id(o), "value_rule": rule,
           "note": "value_id is the identity of the value; address_id and derivation_id identify how it was named and "
                   "derived. value_sha256 hashes the full response value (which includes construction) and is kept for compatibility."}
    if o.kind == "map" and o.map._table is not None:
        out["table_sha256"] = "sha256:" + A.sha256_obj(o.map._table)
        out["equivalence"] = "Two addresses with the same table_sha256 denote the same map (extensional equality)."
    return out


def environment() -> dict:
    """An observation of this runtime. Capabilities are observed, not assumed."""
    mods = {m: importlib.util.find_spec(m) is not None for m in ("numpy", "scipy", "networkx", "sympy")}
    return {
        "protocol": PROTOCOL, "kind": "environment",
        "runtime": "python", "python": sys.version.split()[0], "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "modules": mods,
        "clock": {"logical": "deterministic (the step index)", "wall": "nondeterministic; reported as wall_ns, never hashed"},
        "randomness": "seeded only: registered operations use random.Random(seed) from the address",
        "filesystem": "not used by resolution; POST appends to the execution store",
        "network": "not used by any registered operation (not probed)",
        "subprocess": "not used by any registered operation (not probed)",
        "operations": [{"id": o.id, "executable": not missing_requirements(o), "missing": missing_requirements(o)} for o in REGISTRY],
    }


def envelope(o: Obj, ctx: Ctx) -> dict:
    ops = operations_for(o.kind)
    ops_desc = []
    for x in ops:
        miss = missing_requirements(x)
        ops_desc.append({"id": x.id, "template": o.purl + "/" + x.contract()["template"], "yields": x.yields,
                         "effects": x.effects, "executable_here": not miss, **({"missing": miss} if miss else {}),
                         "contract": "/operations/" + x.id})
    derivation = [{"purl": s["purl"], "operation": s["operation"], "kind": s["kind"]} for s in ctx.steps]
    return {
        "protocol": PROTOCOL,
        "kind": o.kind,
        "purl": o.purl,
        "value": o.value,
        "identity": identity(o),
        "derivation": derivation,
        "execution": {
            "operations": [{"id": s["operation"], "version": operation_version(_by_id(s["operation"]))} for s in ctx.steps],
            "materialized": [{k: v for k, v in m.items() if k != "wall_ns"} for m in ctx.materialized],
            "effects": sorted({_by_id(s["operation"]).effects for s in ctx.steps}),
            "deterministic_sha256": "sha256:" + A.sha256_obj({"purl": o.purl, "kind": o.kind, "value": o.value}),
            "deterministic_sha256_semantics": "H(address, kind, full value): an address-bound result hash. Equal for reruns of one "
                                              "address; never equal across addresses. Compare values with identity.value_id (F-010).",
            "environment_id": environment_id(),
            "wall_ns": {"steps": [s["wall_ns"] for s in ctx.steps], "materialization": [m["wall_ns"] for m in ctx.materialized],
                        "note": "instrument wall clock: nondeterministic, excluded from every hash"},
            "epistemic_status": sorted({_by_id(s["operation"]).epistemic_status for s in ctx.steps}),
        },
        "operations": ops_desc,
        "next": next_links(o),
        "links": {"parent": derivation[-2]["purl"] if len(derivation) > 1 else None, "root": derivation[0]["purl"],
                  "operations": "/operations", "environment": "/environment", "executions": "/executions?purl=" + o.purl},
    }


def _by_id(oid: str) -> Operation:
    return next(o for o in REGISTRY if o.id == oid)


def get(purl: str) -> Tuple[int, dict]:
    """GET semantics: pure resolution. Never writes anything."""
    try:
        o, ctx = resolve(purl)
        return 200, envelope(o, ctx)
    except PurlError as e:
        return e.status, e.doc(canonical(purl) if purl.strip("/") else "/")


def registry_document() -> dict:
    return {"protocol": PROTOCOL, "kind": "operation_registry",
            "semantics": "Operations are looked up here, never evaluated. A PURL is a root constructor followed by operations; "
                         "each operation applies to the kind of object its prefix denotes.",
            "roots": [o.contract()["template"] for o in operations_for("root")],
            "kinds": sorted({o.applies_to for o in REGISTRY} | {o.yields for o in REGISTRY}),
            "operations": [dict(o.contract(), version=operation_version(o), executable_here=not missing_requirements(o)) for o in REGISTRY]}
