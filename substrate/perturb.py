"""Controlled perturbation: recorded interventions and baseline/perturbed comparison.

An intervention is data before it is an action: `Intervention.record()` is what
gets persisted, so every perturbed artifact names the exact change applied.

Metric definitions (all over logical time; t0 = intervention time, H = horizon):

  d_t                 Hamming distance between baseline and perturbed state at t
  D_t                 set of differing bit positions at t
  persistence         #{t in (t0, t0+H] : d_t > 0}
  recovery_time       min{k >= 1 : d_{t0+k} = 0}, or None within the horizon
  max_distance        max_{t > t0} d_t
  amplification       max_distance / d_{t0}     (d_{t0} = size of the injected change)
  spread (ring)       max over t, i in D_t of circular distance(i, injected bit)
  first_escape_time   min{k : D_{t0+k} not subset of D_{t0}} (propagation time)

Classification (exhaustive, mutually exclusive, *relative to the horizon*):

  masked             d_{t0+1} = 0
  recovered          masked is false and d reaches 0 within the horizon
  amplified          never 0 within horizon and max_distance > d_{t0}
  persistent_local   never 0, d_t = d_{t0} and D_t = D_{t0} for all t
  transformed        never 0, d_t <= d_{t0} for all t, but D_t changes

For a deterministic system, d_t = 0 implies d_{t'} = 0 for t' > t (trajectories
that merge stay merged); so masked/recovered are absorbing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .core import hamming


@dataclass
class Intervention:
    kind: str                 # "state_bit_flip" | "state_xor" | "edge_rewire" | "null"
    time: Optional[int] = None
    params: Dict = field(default_factory=dict)
    note: str = "SIMULATED intervention on a computational model; not a physical event."

    def record(self) -> dict:
        return {"kind": self.kind, "time": self.time, "params": self.params, "note": self.note}

    def state_fn(self):
        if self.kind == "state_bit_flip":
            mask = 1 << self.params["bit"]
            return lambda x: x ^ mask
        if self.kind == "state_xor":
            mask = self.params["mask"]
            return lambda x: x ^ mask
        if self.kind == "null":
            return lambda x: x
        raise ValueError("not a state intervention: " + self.kind)

    def apply_to_table(self, table: Sequence[int]) -> List[int]:
        if self.kind == "edge_rewire":
            t = list(table)
            t[self.params["src"]] = self.params["new_dst"]
            return t
        if self.kind == "null":
            return list(table)
        raise ValueError("not a structural intervention: " + self.kind)


def bits_of(mask: int) -> List[int]:
    out, i = [], 0
    while mask:
        if mask & 1:
            out.append(i)
        mask >>= 1; i += 1
    return out


def circ(i: int, j: int, n: int) -> int:
    d = abs(i - j) % n
    return min(d, n - d)


def compare_state_sequences(base: Sequence[int], pert: Sequence[int], t0: int, n_bits: int,
                            injected_bits: Sequence[int]) -> dict:
    """Compare two state sequences indexed by logical time (same length)."""
    if len(base) != len(pert):
        raise ValueError("sequences must have equal length")
    d = [hamming(a, b) for a, b in zip(base, pert)]
    D = [a ^ b for a, b in zip(base, pert)]
    d0 = d[t0]
    after = list(range(t0 + 1, len(d)))
    horizon = len(after)
    zero_at = next((k - t0 for k in after if d[k] == 0), None)
    max_d = max((d[k] for k in after), default=0)
    D0 = D[t0]
    escape = next((k - t0 for k in after if D[k] & ~D0), None)
    spread = 0
    for k in [t0] + after:
        for i in bits_of(D[k]):
            spread = max(spread, min(circ(i, j, n_bits) for j in injected_bits) if injected_bits else 0)

    if d0 == 0:
        cls = "null"  # no change was injected (control)
    elif after and d[t0 + 1] == 0:
        cls = "masked"
    elif zero_at is not None:
        cls = "recovered"
    elif max_d > d0:
        cls = "amplified"
    elif all(D[k] == D0 for k in after):
        cls = "persistent_local"
    else:
        cls = "transformed"

    return {
        "class": cls,
        "horizon": horizon,
        "d0": d0,
        "distance_series": d,
        "persistence": sum(1 for k in after if d[k] > 0),
        "recovery_time": zero_at,
        "max_distance": max_d,
        "amplification": (max_d / d0) if d0 else None,
        "spread": spread,
        "first_escape_time": escape,
        "final_distance": d[-1],
    }


def compare_functional_graphs(a_an: dict, b_an: dict) -> dict:
    """Baseline vs structurally-perturbed functional graph (analyses from
    graph.functional_graph_analysis). Attractor identity is by vertex set."""
    ca = {frozenset(c) for c in a_an["_cycles"]}
    cb = {frozenset(c) for c in b_an["_cycles"]}
    # states whose attractor changed (compared by attractor vertex-set)
    att_a = [frozenset(a_an["_cycles"][c]) for c in a_an["_comp"]]
    att_b = [frozenset(b_an["_cycles"][c]) for c in b_an["_comp"]]
    changed = sum(1 for x, y in zip(att_a, att_b) if x != y)
    tail_changed = sum(1 for x, y in zip(a_an["_tail"], b_an["_tail"]) if x != y)
    return {
        "attractors_removed": len(ca - cb),
        "attractors_added": len(cb - ca),
        "n_components_delta": b_an["n_components"] - a_an["n_components"],
        "n_cyclic_delta": b_an["n_cyclic"] - a_an["n_cyclic"],
        "states_attractor_changed": changed,
        "fraction_attractor_changed": changed / a_an["n_states"],
        "states_transient_changed": tail_changed,
        "garden_of_eden_delta": b_an["n_garden_of_eden"] - a_an["n_garden_of_eden"],
    }
