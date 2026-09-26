"""Maps between representational spaces and what they lose.

For a map P : S_A -> S_B (any total function on a finite set):

  fiber          P^{-1}(y) = {x : P(x) = y}
  kernel         ker P : x ~ x'  iff  P(x) = P(x')   (the induced equivalence)
  info loss      H(X | P(X)) under a stated distribution on X
                 = H(X) - H(P(X)) since P is a function
  reconstructible  iff P is injective on the support of the distribution

For P to carry *autonomous dynamics* of a deterministic f : S_A -> S_A there
must be g with P o f = g o P. This holds iff ker P is a congruence of f:
  P(x) = P(x')  =>  P(f x) = P(f x').
(Established: factor map / homomorphism of dynamical systems; exact
lumpability for Markov chains; bisimulation quotient for LTSs.)

`coarsest_congruence(f, O)` computes the coarsest partition that (i) refines
ker O and (ii) is a congruence of f — i.e. Moore-machine minimisation with
output O. Its number of blocks is the minimum number of distinguishable
states any representation must keep to predict the entire future of the
observable O under f. This is one precise answer to "what is the minimum
information that must survive between two representations?" — relative to a
chosen property O, as the charter anticipated.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Callable, Dict, Hashable, List, Optional, Sequence

from .info import entropy_of_distribution


def fibers(domain: Sequence[int], P: Callable[[int], Hashable]) -> Dict[Hashable, List[int]]:
    out: Dict[Hashable, List[int]] = defaultdict(list)
    for x in domain:
        out[P(x)].append(x)
    return dict(out)


def information_loss(domain: Sequence[int], P: Callable[[int], Hashable],
                     weights: Optional[Sequence[float]] = None) -> dict:
    """Information accounting for P under distribution `weights` (uniform if None).
    Weights are indexed by position in `domain`."""
    n = len(domain)
    w = list(weights) if weights is not None else [1.0] * n
    tot = sum(w)
    p = [wi / tot for wi in w]
    img: Dict[Hashable, float] = defaultdict(float)
    for x, px in zip(domain, p):
        img[P(x)] += px
    h_x = entropy_of_distribution(p)
    h_y = entropy_of_distribution(img.values())
    fib = fibers([x for x, px in zip(domain, p) if px > 0], P)
    sizes = sorted((len(v) for v in fib.values()), reverse=True)
    return {
        "H_X": h_x,
        "H_PX": h_y,
        "H_X_given_PX": h_x - h_y,
        "fraction_lost": ((h_x - h_y) / h_x) if h_x > 0 else 0.0,
        "n_fibers": len(fib),
        "max_fiber": sizes[0] if sizes else 0,
        "fiber_size_histogram": {str(k): sizes.count(k) for k in sorted(set(sizes))},
        "reconstructible_on_support": all(s == 1 for s in sizes),
    }


def compatibility(table: Sequence[int], P: Callable[[int], Hashable]) -> dict:
    """Is ker P a congruence of f? Returns the number of fibers whose images
    under f are split by P (violations), and the induced map g if compatible."""
    fib = fibers(range(len(table)), P)
    g, violations = {}, 0
    for y, xs in fib.items():
        imgs = {P(table[x]) for x in xs}
        if len(imgs) == 1:
            g[y] = next(iter(imgs))
        else:
            violations += 1
    return {"compatible": violations == 0, "violating_fibers": violations,
            "n_fibers": len(fib), "induced_map": g if violations == 0 else None}


def coarsest_congruence(table: Sequence[int], O: Callable[[int], Hashable]) -> List[int]:
    """Moore partition refinement. Returns block id per state.
    Start from ker O; split blocks by (block(x), block(f x)) until stable."""
    n = len(table)
    labels = {}
    block = []
    for x in range(n):
        block.append(labels.setdefault(O(x), len(labels)))
    while True:
        sig = {}
        new = []
        for x in range(n):
            new.append(sig.setdefault((block[x], block[table[x]]), len(sig)))
        if len(sig) == len(set(block)):
            return new
        block = new


def congruence_summary(table: Sequence[int], O: Callable[[int], Hashable]) -> dict:
    blocks = coarsest_congruence(table, O)
    k = len(set(blocks))
    n_obs = len({O(x) for x in range(len(table))})
    return {"n_states": len(table), "n_observable_values": n_obs,
            "n_blocks": k, "bits_required": math.log2(k) if k else 0.0,
            "bits_full_state": math.log2(len(table)),
            "bits_observable": math.log2(n_obs) if n_obs else 0.0}


# --- sequence-level representation change: states -> transitions -------------

def to_transitions(states: Sequence[int]) -> List[int]:
    """Transition representation over GF(2): d_t = x_t XOR x_{t+1}."""
    return [a ^ b for a, b in zip(states, states[1:])]


def from_transitions(x0: int, deltas: Sequence[int]) -> List[int]:
    xs = [x0]
    for d in deltas:
        xs.append(xs[-1] ^ d)
    return xs
