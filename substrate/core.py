"""State spaces and transition maps.

Formal objects (see research/registries/nomenclature.json):

* alphabet            Sigma = {0, 1}
* state space         X_n = Sigma^n, encoded as integers 0 .. 2^n - 1
                      (bit i of the integer is component i of the state)
* deterministic map   f : X_n -> X_n, stored as a lookup table (a list)
* stochastic map      a Markov kernel K(x, .) sampled with an explicit RNG

A deterministic map *is* its table. Names are labels for humans only; two maps
with equal tables are equal (extensional equality).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, List, Sequence

ALPHABET = (0, 1)


# ---------------------------------------------------------------------------
# State space
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StateSpace:
    """X_n = {0,1}^n. Mathematical domain and executable domain coincide only
    for small n; `size` makes the resource boundary explicit."""

    n_bits: int

    @property
    def size(self) -> int:
        return 1 << self.n_bits

    def states(self) -> range:
        return range(self.size)

    def to_bits(self, x: int) -> List[int]:
        return [(x >> i) & 1 for i in range(self.n_bits)]

    def from_bits(self, bits: Sequence[int]) -> int:
        return sum((b & 1) << i for i, b in enumerate(bits))

    def fmt(self, x: int) -> str:
        """Most-significant bit first, fixed width."""
        return format(x, "0{}b".format(self.n_bits)) if self.n_bits else ""


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def popcount(x: int) -> int:
    return bin(x).count("1")


# ---------------------------------------------------------------------------
# Deterministic maps
# ---------------------------------------------------------------------------

@dataclass
class DeterministicMap:
    name: str
    n_bits: int
    table: List[int]
    params: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        size = 1 << self.n_bits
        if len(self.table) != size:
            raise ValueError("table length {} != 2^{}".format(len(self.table), self.n_bits))
        for y in self.table:
            if not 0 <= y < size:
                raise ValueError("table value out of range: {}".format(y))

    def __call__(self, x: int) -> int:
        return self.table[x]

    @property
    def space(self) -> StateSpace:
        return StateSpace(self.n_bits)

    def is_injective(self) -> bool:
        return len(set(self.table)) == len(self.table)

    def describe(self) -> dict:
        return {"name": self.name, "n_bits": self.n_bits, "params": self.params}

    @classmethod
    def from_function(cls, name: str, n_bits: int, fn: Callable[[int], int], **params) -> "DeterministicMap":
        return cls(name, n_bits, [fn(x) for x in range(1 << n_bits)], dict(params))


# --- one-bit maps: the complete set Sigma -> Sigma (there are exactly 4) ----

def one_bit_maps() -> List[DeterministicMap]:
    return [
        DeterministicMap("identity", 1, [0, 1]),
        DeterministicMap("not", 1, [1, 0]),
        DeterministicMap("const0", 1, [0, 0]),
        DeterministicMap("const1", 1, [1, 1]),
    ]


# --- n-bit families -------------------------------------------------------

def increment(n: int) -> DeterministicMap:
    m = (1 << n) - 1
    return DeterministicMap.from_function("increment", n, lambda x: (x + 1) & m)


def eca(rule: int, n: int) -> DeterministicMap:
    """Elementary cellular automaton (Wolfram numbering) on a ring of n cells.
    Cell i's neighbourhood is (i-1, i, i+1) mod n; bit i is cell i."""
    if not 0 <= rule <= 255:
        raise ValueError("rule must be 0..255")

    def step(x: int) -> int:
        y = 0
        for i in range(n):
            l = (x >> ((i + 1) % n)) & 1  # left neighbour = higher index
            c = (x >> i) & 1
            r = (x >> ((i - 1) % n)) & 1
            if (rule >> ((l << 2) | (c << 1) | r)) & 1:
                y |= 1 << i
        return y

    return DeterministicMap.from_function("eca{}".format(rule), n, step, rule=rule)


def eca_step(rule: int, n: int, x: int) -> int:
    """Single ECA step without building a table (for n too large to tabulate)."""
    y = 0
    for i in range(n):
        l = (x >> ((i + 1) % n)) & 1
        c = (x >> i) & 1
        r = (x >> ((i - 1) % n)) & 1
        if (rule >> ((l << 2) | (c << 1) | r)) & 1:
            y |= 1 << i
    return y


def random_map(n: int, seed: int) -> DeterministicMap:
    """Uniform random mapping X_n -> X_n (each image i.i.d. uniform)."""
    rng = random.Random(seed)
    size = 1 << n
    return DeterministicMap("random_map", n, [rng.randrange(size) for _ in range(size)], {"seed": seed})


def random_permutation(n: int, seed: int) -> DeterministicMap:
    rng = random.Random(seed)
    t = list(range(1 << n))
    rng.shuffle(t)
    return DeterministicMap("random_permutation", n, t, {"seed": seed})


# ---------------------------------------------------------------------------
# Stochastic maps (Markov kernels)
# ---------------------------------------------------------------------------

class BitFlipChannel:
    """Each bit independently flips with probability p per step.
    K(x, y) = p^d (1-p)^(n-d), d = hamming(x, y)."""

    def __init__(self, n_bits: int, p: float):
        self.n_bits, self.p = n_bits, p
        self.name = "bitflip_channel"

    def sample(self, x: int, rng: random.Random) -> int:
        for i in range(self.n_bits):
            if rng.random() < self.p:
                x ^= 1 << i
        return x

    def describe(self) -> dict:
        return {"name": self.name, "n_bits": self.n_bits, "p": self.p}


class TransitionMarkovBit:
    """One-bit process whose *transition* (flip / no-flip) is first-order Markov:
    P(flip_t = 1 | flip_{t-1} = a) = q[a].

    In the state representation this is a second-order process (the next state
    depends on x_t and x_{t-1}); in the transition representation it is first
    order. Used to test whether transition history carries predictive
    information beyond the current state (H-001)."""

    def __init__(self, q0: float, q1: float):
        self.q = (q0, q1)
        self.name = "transition_markov_bit"

    def generate(self, length: int, rng: random.Random, x0: int = 0, d0: int = 0) -> List[int]:
        xs, d = [x0], d0
        for _ in range(length - 1):
            d = 1 if rng.random() < self.q[d] else 0
            xs.append(xs[-1] ^ d)
        return xs

    def describe(self) -> dict:
        return {"name": self.name, "q0": self.q[0], "q1": self.q[1]}


class StateMarkovBit:
    """First-order Markov chain on {0,1}: P(x_{t+1}=1 | x_t=a) = r[a]."""

    def __init__(self, r0: float, r1: float):
        self.r = (r0, r1)
        self.name = "state_markov_bit"

    def generate(self, length: int, rng: random.Random, x0: int = 0) -> List[int]:
        xs = [x0]
        for _ in range(length - 1):
            xs.append(1 if rng.random() < self.r[xs[-1]] else 0)
        return xs

    def describe(self) -> dict:
        return {"name": self.name, "r0": self.r[0], "r1": self.r[1]}
