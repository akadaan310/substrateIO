"""Transition events and traces.

Distinctions enforced here (charter §8, §20):

* bare state        s_t                         -> an int
* bare transition   (s_t, s_{t+1})              -> a pair; carries no more than that
* transition event  e_t = (s_t, s_{t+1}, t, ...) -> `Event`: a *recorded* transition
                    with logical time t and optional wall-clock observation
* trace             tau = (e_0, ..., e_{n-1})    -> `Trace`

Two clocks are kept strictly separate:

* logical time t (step index) is part of the model and is deterministic;
* wall-clock time is an *observation of the instrument's execution*, is
  non-deterministic, and is never included in reproducibility hashes. It
  establishes ordering of the instrument's own steps, not causality.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class Event:
    t: int                      # logical time of the source state
    src: int
    dst: int
    wall_ns: Optional[int] = None   # instrument wall clock (non-deterministic)
    label: str = ""                 # e.g. "step", "intervention"

    @property
    def delta(self) -> int:
        """Changed-bit mask. For Sigma={0,1} the XOR difference is the
        transition symbol: it is the discrete difference Δx_t over GF(2)."""
        return self.src ^ self.dst

    def deterministic(self) -> dict:
        return {"t": self.t, "src": self.src, "dst": self.dst, "label": self.label}


@dataclass
class Trace:
    n_bits: int
    events: List[Event] = field(default_factory=list)
    x0: int = 0
    meta: dict = field(default_factory=dict)

    @property
    def states(self) -> List[int]:
        return [self.x0] + [e.dst for e in self.events]

    @property
    def deltas(self) -> List[int]:
        return [e.delta for e in self.events]

    def deterministic(self) -> dict:
        return {"n_bits": self.n_bits, "x0": self.x0, "states": self.states,
                "labels": [e.label for e in self.events]}

    def wall_intervals_ns(self) -> List[int]:
        w = [e.wall_ns for e in self.events if e.wall_ns is not None]
        return [b - a for a, b in zip(w, w[1:])]


def run(step: Callable[[int], int], n_bits: int, x0: int, steps: int,
        interventions: Optional[dict] = None, clock: bool = True) -> Trace:
    """Iterate `step` from x0. `interventions` maps logical time t -> a function
    applied to the state *after* step t-1 has produced it and *before* step t
    reads it. Each intervention is recorded as its own event, so the trace
    never hides that the system was touched."""
    interventions = interventions or {}
    tr = Trace(n_bits=n_bits, x0=x0)
    x = x0
    t0 = time.perf_counter_ns() if clock else None
    for t in range(steps):
        if t in interventions:
            y = interventions[t](x)
            tr.events.append(Event(t, x, y, (time.perf_counter_ns() - t0) if clock else None, "intervention"))
            x = y
        y = step(x)
        tr.events.append(Event(t, x, y, (time.perf_counter_ns() - t0) if clock else None, "step"))
        x = y
    return tr


def step_states(tr: Trace) -> List[int]:
    """States at logical times 0..steps, *after* any intervention at that time
    (i.e. the state the dynamics actually read). Comparable across a baseline
    and a perturbed trace index by index."""
    out = []
    for e in tr.events:
        if e.label == "step":
            out.append(e.src)
    if tr.events:
        out.append(tr.events[-1].dst)
    return out
