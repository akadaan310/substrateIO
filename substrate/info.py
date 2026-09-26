"""Plug-in (maximum-likelihood) information estimators, in bits.

Caveat recorded in research/registries/failures.json (F-003 style limitations):
plug-in entropy estimates are negatively biased for small samples (Miller-Madow
correction ~ (K-1)/(2N ln 2)). Experiments that compare conditional entropies
must use samples large enough that the bias is below the effect size, and must
report sample size.
"""

from __future__ import annotations

import math
import zlib
from collections import Counter
from typing import Hashable, Iterable, List, Sequence, Tuple


def entropy_from_counts(counts: Iterable[int]) -> float:
    counts = [c for c in counts if c > 0]
    n = sum(counts)
    if n == 0:
        return 0.0
    return -sum((c / n) * math.log2(c / n) for c in counts)


def entropy(xs: Iterable[Hashable]) -> float:
    return entropy_from_counts(Counter(xs).values())


def entropy_of_distribution(p: Iterable[float]) -> float:
    return -sum(q * math.log2(q) for q in p if q > 0)


def blocks(xs: Sequence, k: int) -> List[Tuple]:
    return [tuple(xs[i:i + k]) for i in range(len(xs) - k + 1)]


def block_entropy(xs: Sequence, k: int) -> float:
    return entropy(blocks(xs, k)) if k > 0 else 0.0


def conditional_entropy_next(xs: Sequence, k: int) -> float:
    """H(X_{t+1} | X_{t-k+1..t}) estimated as H_{k+1} - H_k over aligned blocks."""
    if k == 0:
        return entropy(xs[1:])
    joint = blocks(xs, k + 1)
    ctx = [b[:-1] for b in joint]
    return entropy(joint) - entropy(ctx)


def conditional_entropy_pairs(pairs: Sequence[Tuple[Hashable, Hashable]]) -> float:
    """H(Y | X) from (x, y) samples."""
    return entropy(pairs) - entropy(x for x, _ in pairs)


def mutual_information_pairs(pairs: Sequence[Tuple[Hashable, Hashable]]) -> float:
    return entropy(x for x, _ in pairs) + entropy(y for _, y in pairs) - entropy(pairs)


def conditional_mutual_information(triples: Sequence[Tuple[Hashable, Hashable, Hashable]]) -> float:
    """I(X; Y | Z) from (x, y, z) samples = H(X,Z)+H(Y,Z)-H(X,Y,Z)-H(Z)."""
    return (entropy((x, z) for x, _, z in triples) + entropy((y, z) for _, y, z in triples)
            - entropy(triples) - entropy(z for _, _, z in triples))


def miller_madow_bias(n_categories: int, n_samples: int) -> float:
    return (n_categories - 1) / (2 * n_samples * math.log(2)) if n_samples else float("inf")


def compressed_bits(data: bytes, level: int = 9) -> int:
    """zlib-compressed length in bits: a *computable upper-bound proxy* for
    description length, NOT Kolmogorov complexity."""
    return 8 * len(zlib.compress(data, level))


def pack_bits(bits: Sequence[int]) -> bytes:
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for j, b in enumerate(bits[i:i + 8]):
            byte |= (b & 1) << j
        out.append(byte)
    return bytes(out)
