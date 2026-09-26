"""A SIMULATED layered abstraction boundary for cross-layer propagation studies.

Layers (a hypothesis about useful cut points, not a claim about real hardware):

  L0  stored codeword bits      (a storage code over a 4-bit data nibble)
  L1  architectural value       (decoder output + decoder status)
  L2  execution trace           (per-step (value read, branch taken, accumulator))
  L3  observable output         (alarm flag, max, checksum, or DUE signal)

Storage codes (established coding theory):
  none     4 data bits, no redundancy
  parity   4+1 even parity: detects any odd-weight error, corrects none
  hamming  Hamming(7,4): corrects any single-bit error (SEC); a double error is
           miscorrected to a wrong codeword
  secded   extended Hamming(8,4): corrects single, detects double (SECDED)

Every fault here is an *injected, simulated* state change on a Python integer.
It is not a radiation event, charge deposition, or device-level upset, and no
result produced here is evidence about physical SEU rates or mechanisms.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

# --- storage codes ---------------------------------------------------------

# Hamming(7,4), positions 1..7 = p1 p2 d1 p3 d2 d3 d4 (bit index = position-1)


def _bit(x: int, i: int) -> int:
    return (x >> i) & 1


def ham74_encode(d: int) -> int:
    d1, d2, d3, d4 = (_bit(d, i) for i in range(4))
    p1 = d1 ^ d2 ^ d4
    p2 = d1 ^ d3 ^ d4
    p3 = d2 ^ d3 ^ d4
    bits = [p1, p2, d1, p3, d2, d3, d4]
    return sum(b << i for i, b in enumerate(bits))


def ham74_syndrome(c: int) -> int:
    s = 0
    for pos in range(1, 8):
        if _bit(c, pos - 1):
            s ^= pos
    return s


def ham74_data(c: int) -> int:
    return _bit(c, 2) | (_bit(c, 4) << 1) | (_bit(c, 5) << 2) | (_bit(c, 6) << 3)


@dataclass
class Decoded:
    value: int
    status: str            # "ok" | "corrected" | "detected" (uncorrectable)
    located_bit: int = -1  # decoder's inferred error location (model-relative)


class Code:
    name = "abstract"
    n = 0

    def encode(self, d: int) -> int: ...
    def decode(self, c: int) -> Decoded: ...


class NoCode(Code):
    name, n = "none", 4

    def encode(self, d): return d
    def decode(self, c): return Decoded(c & 0xF, "ok")


class ParityCode(Code):
    name, n = "parity", 5

    def encode(self, d):
        return d | ((bin(d).count("1") & 1) << 4)

    def decode(self, c):
        if bin(c).count("1") & 1:
            return Decoded(c & 0xF, "detected")
        return Decoded(c & 0xF, "ok")


class Hamming74(Code):
    name, n = "hamming", 7

    def encode(self, d): return ham74_encode(d)

    def decode(self, c):
        s = ham74_syndrome(c)
        if s == 0:
            return Decoded(ham74_data(c), "ok")
        c2 = c ^ (1 << (s - 1))
        # The syndrome *assumes* a single-bit error. Under a double error it
        # points at a wrong location and the "correction" corrupts the data.
        return Decoded(ham74_data(c2), "corrected", s - 1)


class SECDED84(Code):
    name, n = "secded", 8

    def encode(self, d):
        c = ham74_encode(d)
        return c | ((bin(c).count("1") & 1) << 7)

    def decode(self, c):
        inner = c & 0x7F
        s = ham74_syndrome(inner)
        overall = bin(c).count("1") & 1
        if s == 0 and overall == 0:
            return Decoded(ham74_data(inner), "ok")
        if overall == 1:  # odd number of errors: assume single, correct
            if s == 0:
                return Decoded(ham74_data(inner), "corrected", 7)
            return Decoded(ham74_data(inner ^ (1 << (s - 1))), "corrected", s - 1)
        return Decoded(ham74_data(inner), "detected")  # even, nonzero syndrome


CODES = {c.name: c for c in (NoCode(), ParityCode(), Hamming74(), SECDED84())}


# --- the program (L2) ----------------------------------------------------------

ALARM_THRESHOLD = 12


def run_program(read_word) -> Tuple[List[Tuple], Dict]:
    """Reads 8 words, one per step (word j at step j). Computes:
       max value, alarm = (max >= ALARM_THRESHOLD), checksum = sum mod 16,
       with a branch per step (value >= 8 takes branch A).
    If the decoder reports 'detected', the program halts with a DUE
    (detected unrecoverable error) output — a fail-stop policy."""
    trace, acc, mx = [], 0, 0
    for j in range(8):
        dec = read_word(j, j)
        if dec.status == "detected":
            trace.append((j, "DUE", None, acc))
            return trace, {"DUE": True}
        v = dec.value
        branch = "A" if v >= 8 else "B"
        acc = (acc + v) & 0xF
        mx = max(mx, v)
        trace.append((j, v, branch, acc))
    return trace, {"DUE": False, "alarm": mx >= ALARM_THRESHOLD, "max": mx, "checksum": acc}


@dataclass
class Injection:
    word: int
    bits: Tuple[int, ...]   # codeword bit positions flipped (one => single, two => double)
    time: int               # logical time of the flip (flip happens before step `time` reads)

    def record(self) -> dict:
        return {"word": self.word, "bits": list(self.bits), "time": self.time,
                "note": "SIMULATED injected bit flip; not a physical event"}


def execute(code: Code, data: Sequence[int], inj: Injection = None) -> dict:
    mem = [code.encode(d) for d in data]
    decoded_log = {}

    def read(j, t):
        c = mem[j]
        if inj is not None and inj.word == j and inj.time <= t:
            for b in inj.bits:
                c ^= 1 << b
        dec = code.decode(c)
        decoded_log[j] = dec
        return dec

    trace, out = run_program(read)
    return {"trace": trace, "out": out, "decoded": decoded_log}


def classify(code: Code, data: Sequence[int], inj: Injection) -> dict:
    """Run baseline and injected, then classify the outcome at every layer."""
    base = execute(code, data)
    pert = execute(code, data, inj)
    j = inj.word
    read_happened_after = inj.time <= j        # was the flip present when word j was read?
    dec_b = base["decoded"].get(j)
    dec_p = pert["decoded"].get(j)

    # L0: codeword distance at the time of the read
    l0_distance = len(inj.bits) if read_happened_after else 0
    # L1: architectural value
    if dec_p is None:
        l1 = "not_read"
        l1_dist = 0
    elif dec_p.status == "detected":
        l1 = "detected"
        l1_dist = 0
    else:
        l1_dist = bin(dec_p.value ^ dec_b.value).count("1")
        if dec_p.status == "corrected" and l1_dist == 0:
            l1 = "corrected"
        elif l1_dist == 0:
            l1 = "masked" if l0_distance else "not_present_at_read"
        elif dec_p.status == "corrected":
            l1 = "miscorrected"
        else:
            l1 = "propagated"
    # L2: trace divergence
    tb, tp = base["trace"], pert["trace"]
    l2_diff = sum(1 for a, b in zip(tb, tp) if a != b) + abs(len(tb) - len(tp))
    branch_diff = sum(1 for a, b in zip(tb, tp) if a[2] != b[2])
    # L3: output
    ob, op = base["out"], pert["out"]
    fields = ["alarm", "max", "checksum"]
    if op.get("DUE"):
        outcome = "DUE"
        l3_diff = None
    else:
        l3_diff = sum(1 for f in fields if ob[f] != op[f])
        if l3_diff == 0:
            if not read_happened_after:
                outcome = "masked_timing"
            elif l1 == "corrected":
                outcome = "corrected"
            elif l1_dist == 0:
                outcome = "masked_architectural"
            else:
                outcome = "masked_logical"
        else:
            outcome = "SDC"
    # Did the decoder's inferred location match the true location?
    located_ok = None
    if dec_p is not None and dec_p.status == "corrected":
        located_ok = (len(inj.bits) == 1 and dec_p.located_bit == inj.bits[0])

    return {
        "injection": inj.record(),
        "outcome": outcome,
        "L0_distance": l0_distance,
        "L1": l1,
        "L1_value_distance": l1_dist,
        "L2_steps_differing": l2_diff,
        "L2_branches_differing": branch_diff,
        "L3_fields_differing": l3_diff,
        "L3_fields": [f for f in fields if not op.get("DUE") and ob[f] != op[f]],
        "decoder_location_correct": located_ok,
        # normalised distances (for attenuation/amplification ratios)
        "norm": {
            "L0": l0_distance / code.n,
            "L1": l1_dist / 4,
            "L2": l2_diff / 8,
            "L3": (l3_diff / 3) if l3_diff is not None else None,
        },
    }
