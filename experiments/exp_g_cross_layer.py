"""EXP-G — cross-layer propagation across a SIMULATED abstraction boundary.

Model (substrate.layers): 8 data nibbles stored under a code (none, parity,
Hamming(7,4) SEC, extended Hamming(8,4) SECDED) -> decoded architectural value
-> an 8-step program trace -> output (alarm, max, checksum) or DUE.

Injection campaign (exhaustive over the model, per dataset):
  single-bit flips: every word x every codeword bit x every injection time 0..8
  double-bit flips: every word x every pair of codeword bits, at time 0

Outcome taxonomy mapped to established dependability terms (Avizienis et al.
2004; soft-error literature, e.g. Mukherjee 2008): corrected, DUE (detected
unrecoverable error), SDC (silent data corruption), masked (timing /
architectural / logical).

EVERYTHING HERE IS SIMULATED. Injected flips stand in for state upsets; they
are not radiation events and say nothing about physical upset rates.
"""

import itertools
import random
from collections import Counter

from substrate.layers import CODES, Injection, classify
from . import check, ev

SPEC = {
    "experiment_id": "EXP-G",
    "title": "Cross-layer propagation through a simulated abstraction boundary",
    "question": "How does a one-bit difference at a storage layer propagate, attenuate, amplify or vanish across architectural, trace and output layers, and does detecting an inconsistency identify its cause?",
    "hypotheses": ["H-005", "H-011", "H-013"],
    "objective": "Exhaustive fault-injection campaign in a four-layer model under four storage codes.",
    "model": "substrate.layers (8 nibbles, 4 codes, 8-step program).",
    "procedure": "For each dataset, code, injection: classify outcome per layer; aggregate.",
    "expected_result": "Single flips present at read: hamming/secded 100% corrected; parity 100% DUE; none 100% propagated at L1. Double flips: secded 100% DUE; hamming decoder location wrong 100%. Distance non-monotone across layers in the unprotected case.",
    "falsification_condition": "Any SDC from a single flip under hamming/secded; any undetected single flip under parity; decoder-identified location correct for any double flip under hamming.",
    "epistemic_status_of_result": "SIMULATED (model only; no physical claim)",
    "post_hoc_checks": ["G8"],
    "notes": "First execution: 0% logical masking in the unprotected case because the checksum output depends on every data bit. G8 (post-hoc) measures masking per output observable.",
}

CONFIG = {"seed": 314159, "n_datasets": 20}


def run(config):
    rng = random.Random(config["seed"])
    datasets = [[rng.randrange(16) for _ in range(8)] for _ in range(config["n_datasets"])]
    res = {}
    for cname, code in CODES.items():
        single, double = Counter(), Counter()
        l1_single = Counter()
        loc_single, loc_double = Counter(), Counter()
        nonmono, amp_l2 = 0, Counter()
        by_observable = {"all": Counter(), "alarm": Counter(), "max": Counter(), "checksum": Counter()}
        n_present = 0
        for data in datasets:
            for j in range(8):
                for b in range(code.n):
                    for t in range(9):
                        r = classify(code, data, Injection(j, (b,), t))
                        single[r["outcome"]] += 1
                        if t <= j:
                            n_present += 1
                            l1_single[r["L1"]] += 1
                            if cname == "none":
                                amp_l2[r["L2_steps_differing"]] += 1
                                for obs in by_observable:
                                    hit = r["L3_fields"] if obs == "all" else [f for f in r["L3_fields"] if f == obs]
                                    by_observable[obs]["SDC" if hit else "masked_logical"] += 1
                                nz = r["norm"]
                                if nz["L3"] is not None and nz["L2"] > nz["L1"] and nz["L3"] < nz["L2"]:
                                    nonmono += 1
                        if r["decoder_location_correct"] is not None:
                            loc_single[r["decoder_location_correct"]] += 1
                for b1, b2 in itertools.combinations(range(code.n), 2):
                    r = classify(code, data, Injection(j, (b1, b2), 0))
                    double[r["outcome"]] += 1
                    if r["decoder_location_correct"] is not None:
                        loc_double[r["decoder_location_correct"]] += 1
        res[cname] = {
            "single_outcomes": dict(sorted(single.items())),
            "single_L1_when_present": dict(sorted(l1_single.items())),
            "single_present_at_read": n_present,
            "double_outcomes": dict(sorted(double.items())),
            "decoder_location_correct_single": {str(k): v for k, v in sorted(loc_single.items())},
            "decoder_location_correct_double": {str(k): v for k, v in sorted(loc_double.items())},
        }
        if cname == "none":
            res[cname]["L2_steps_differing_hist"] = {str(k): v for k, v in sorted(amp_l2.items())}
            res[cname]["amplified_at_L2_then_attenuated_at_L3"] = nonmono
            res[cname]["single_present_by_output_observable"] = {k: dict(sorted(v.items())) for k, v in by_observable.items()}

    def frac(counter, key):
        tot = sum(counter.values())
        return counter.get(key, 0) / tot if tot else 0.0

    none = res["none"]
    sdc_none = none["single_outcomes"].get("SDC", 0)
    logical = none["single_outcomes"].get("masked_logical", 0)
    checks = [
        check("G1", "hamming & secded: every single flip present at read is corrected (no SDC, no DUE)",
              all(res[c]["single_L1_when_present"] == {"corrected": res[c]["single_present_at_read"]} for c in ("hamming", "secded"))),
        check("G2", "parity: every single flip present at read is detected (DUE)",
              res["parity"]["single_L1_when_present"] == {"detected": res["parity"]["single_present_at_read"]}),
        check("G3", "none: every single flip present at read propagates to L1",
              none["single_L1_when_present"] == {"propagated": none["single_present_at_read"]}),
        check("G4", "secded: every double flip is detected (DUE)",
              list(res["secded"]["double_outcomes"]) == ["DUE"]),
        check("G5", "hamming: decoder-inferred error location is wrong for every double flip",
              res["hamming"]["decoder_location_correct_double"] == {"False": sum(res["hamming"]["double_outcomes"].values())},
              res["hamming"]["decoder_location_correct_double"]),
        check("G6", "hamming: decoder-inferred location is right for every single flip it corrects",
              list(res["hamming"]["decoder_location_correct_single"]) == ["True"]),
        check("G7", "none: some flips are amplified at L2 and attenuated at L3 (distance non-monotone across layers)",
              none["amplified_at_L2_then_attenuated_at_L3"] > 0, none["amplified_at_L2_then_attenuated_at_L3"]),
        # POST-HOC (added after the first execution showed 0% logical masking with the full output):
        check("G8", "POST-HOC: logical-masking fraction differs across output observables (masking is observable-relative)",
              len({round(frac(Counter(v), "masked_logical"), 6) for v in none["single_present_by_output_observable"].values()}) > 1,
              {k: round(frac(Counter(v), "masked_logical"), 6) for k, v in none["single_present_by_output_observable"].items()}),
    ]
    evidence = [
        ev("single_outcomes", "Outcome counts for single-bit injections per storage code (SIMULATED).",
           {c: r["single_outcomes"] for c, r in res.items()}, domain="simulated"),
        ev("double_outcomes", "Outcome counts for double-bit injections per storage code (SIMULATED).",
           {c: r["double_outcomes"] for c, r in res.items()}, domain="simulated"),
        ev("detection_vs_location", "Hamming(7,4) decoder: inferred error location correct? single vs double flips (SIMULATED).",
           {"single": res["hamming"]["decoder_location_correct_single"], "double": res["hamming"]["decoder_location_correct_double"]}, domain="simulated"),
        ev("logical_masking_fraction", "Unprotected storage: fraction of single flips present at read that were logically masked by program semantics (SIMULATED; property of this toy program).",
           {"masked_logical": logical, "SDC": sdc_none, "fraction_masked_logical": round(logical / (logical + sdc_none), 6)}, domain="simulated"),
        ev("masking_by_observable", "Unprotected storage, single flips present at read: SDC vs logically masked, for different output observables (SIMULATED; post-hoc analysis).",
           none["single_present_by_output_observable"], domain="simulated"),
        ev("nonmonotone", "Unprotected storage: count of injections whose normalised distance grows L1->L2 then shrinks L2->L3 (SIMULATED).",
           none["amplified_at_L2_then_attenuated_at_L3"], domain="simulated"),
    ]
    return {"deterministic": {"datasets": datasets, "results": res}, "nondeterministic": {}, "checks": checks, "evidence": evidence}
