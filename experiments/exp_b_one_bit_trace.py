"""EXP-B — repeated one-bit transitions producing traces.

Tests H-001 (does transition history carry predictive information about the
next state beyond the current state?) and H-002 (does the transition
representation expose structure the state representation hides?) on three
sources whose ground truth is known by construction:

  iid        fair coin, order 0
  state_mk   first-order Markov in state space
  trans_mk   first-order Markov in *transition* space (flip persistence) —
             second-order in state space

Measured: H(X_{t+1}|X_t), H(X_{t+1}|X_t,X_{t-1}), their difference
I(X_{t+1}; X_{t-1} | X_t), and the same quantities for d_t = x_t XOR x_{t+1}.
"""

import random
import statistics

from substrate.core import one_bit_maps, StateMarkovBit, TransitionMarkovBit
from substrate.info import (conditional_entropy_next, entropy, miller_madow_bias,
                            compressed_bits, pack_bits, conditional_entropy_pairs)
from substrate.projection import to_transitions
from substrate.trace import run as run_trace
from . import check, ev

SPEC = {
    "experiment_id": "EXP-B",
    "title": "Repeated one-bit transitions producing a trace",
    "question": "Does transition history contain predictive information about future states beyond the current state? What changes when transitions, not states, are the symbols?",
    "hypotheses": ["H-001", "H-002"],
    "objective": "Produce traces (deterministic and stochastic), then measure conditional entropies in state and transition representations.",
    "model": "NOT map (deterministic); iid, first-order state-Markov, and transition-Markov one-bit sources.",
    "procedure": "Generate traces with recorded seed; plug-in entropy estimates; compare context depths 1 and 2; compare representations.",
    "expected_result": "CMI I(X_{t+1};X_{t-1}|X_t) ~ 0 for iid and state-Markov sources; > 0 for the transition-Markov source. Entropy rate equal in both representations.",
    "falsification_condition": "CMI for the state-Markov source exceeds 10x the Miller-Madow bias bound, or CMI for the transition-Markov source is below it; or entropy-rate estimates differ between representations by more than 0.01 bit.",
    "epistemic_status_of_result": "SIMULATED",
    "post_hoc_checks": ["B8"],
    "notes": "B8 was added after the first execution; it is exploratory, not a pre-registered prediction.",
}

CONFIG = {"seed": 20260926, "length": 200000, "deterministic_steps": 64,
          "state_mk": [0.2, 0.7], "trans_mk": [0.1, 0.8]}


def cmi_next(xs):
    return conditional_entropy_next(xs, 1) - conditional_entropy_next(xs, 2)


def run(config):
    rng = random.Random(config["seed"])
    L = config["length"]

    # deterministic part: NOT map trace, with events and wall-clock observation
    not_map = [m for m in one_bit_maps() if m.name == "not"][0]
    tr = run_trace(not_map, 1, 0, config["deterministic_steps"], clock=True)
    det_states = tr.states
    det_deltas = tr.deltas
    wall = tr.wall_intervals_ns()

    sources = {
        "iid": [rng.randrange(2) for _ in range(L)],
        "state_mk": StateMarkovBit(*config["state_mk"]).generate(L, rng),
        "trans_mk": TransitionMarkovBit(*config["trans_mk"]).generate(L, rng),
    }
    bias = miller_madow_bias(8, L)  # 8 = number of length-3 binary blocks
    res = {}
    for name, xs in sources.items():
        ds = to_transitions(xs)
        # integer finite differences over {0,1} ⊂ Z
        d1 = [b - a for a, b in zip(xs, xs[1:])]
        d2 = [xs[t + 1] - 2 * xs[t] + xs[t - 1] for t in range(1, len(xs) - 1)]
        sign_given = conditional_entropy_pairs([((xs[t], ds[t]), d1[t]) for t in range(len(ds))])
        res[name] = {
            "H_X": entropy(xs),
            "H_next_given_1": conditional_entropy_next(xs, 1),
            "H_next_given_2": conditional_entropy_next(xs, 2),
            "H_next_given_3": conditional_entropy_next(xs, 3),
            "CMI_state_hist": cmi_next(xs),
            "H_D": entropy(ds),
            "H_Dnext_given_1": conditional_entropy_next(ds, 1),
            "H_Dnext_given_2": conditional_entropy_next(ds, 2),
            "CMI_trans_hist": cmi_next(ds),
            "H_intdiff_given_state_and_xor": sign_given,
            "second_difference_hist": {str(v): d2.count(v) for v in sorted(set(d2))},
            "transition_rate": sum(ds) / len(ds),
            "state_ctx_curve": [conditional_entropy_next(xs, k) for k in range(0, 7)],
            "trans_ctx_curve": [conditional_entropy_next(ds, k) for k in range(0, 7)],
            "zlib_bits_state": compressed_bits(pack_bits(xs)),
            "zlib_bits_trans": compressed_bits(pack_bits(ds)),
        }
    for v in res.values():
        v.update({k: round(v[k], 9) for k in v if isinstance(v[k], float)})
        v["state_ctx_curve"] = [round(h, 9) for h in v["state_ctx_curve"]]
        v["trans_ctx_curve"] = [round(h, 9) for h in v["trans_ctx_curve"]]

    thr = 10 * bias
    checks = [
        check("B1", "NOT trace alternates with period 2", det_states[:4] == [0, 1, 0, 1] and all(d == 1 for d in det_deltas)),
        check("B2", "state-Markov source: history beyond x_t carries no information (CMI < 10*bias)",
              res["state_mk"]["CMI_state_hist"] < thr, res["state_mk"]["CMI_state_hist"]),
        check("B3", "iid source: CMI < 10*bias", res["iid"]["CMI_state_hist"] < thr, res["iid"]["CMI_state_hist"]),
        check("B4", "transition-Markov source: history carries information beyond x_t (CMI > 10*bias)",
              res["trans_mk"]["CMI_state_hist"] > thr, res["trans_mk"]["CMI_state_hist"]),
        check("B5", "transition-Markov source is first order in transition space (CMI_trans < 10*bias)",
              res["trans_mk"]["CMI_trans_hist"] < thr, res["trans_mk"]["CMI_trans_hist"]),
        check("B6", "entropy rate (depth-3 state ctx vs depth-2 transition ctx) agree within 0.01 bit for all sources",
              all(abs(r["H_next_given_3"] - r["H_Dnext_given_2"]) < 0.01 for r in res.values()),
              {k: round(r["H_next_given_3"] - r["H_Dnext_given_2"], 6) for k, r in res.items()}),
        # POST-HOC (added after the first execution revealed it; see DISC-001):
        check("B8", "POST-HOC: state-Markov source needs deeper context in transition space: H(D|2 prev D) - H(X|1 prev X) > 10*bias",
              res["state_mk"]["H_Dnext_given_2"] - res["state_mk"]["H_next_given_1"] > thr,
              round(res["state_mk"]["H_Dnext_given_2"] - res["state_mk"]["H_next_given_1"], 6)),
        check("B7", "integer first difference adds no information beyond (x_t, XOR transition)",
              all(r["H_intdiff_given_state_and_xor"] < 1e-9 for r in res.values())),
    ]
    evidence = [
        ev("cmi_table", "Estimated I(X_{{t+1}}; X_{{t-1}} | X_t) (bits) per source, N={}, plug-in; Miller-Madow bias bound {:.2e}.".format(L, bias),
           {k: r["CMI_state_hist"] for k, r in res.items()}),
        ev("trans_order", "Transition-Markov source: CMI in state space vs transition space.",
           {"state_space": res["trans_mk"]["CMI_state_hist"], "transition_space": res["trans_mk"]["CMI_trans_hist"]}),
        ev("entropy_rates", "Conditional entropy estimates in both representations.",
           {k: {"state_ctx3": r["H_next_given_3"], "trans_ctx2": r["H_Dnext_given_2"]} for k, r in res.items()}),
        ev("ctx_curves", "Conditional entropy of next symbol vs context depth k=0..6, in state and transition representations.",
           {k: {"state": r["state_ctx_curve"], "transition": r["trans_ctx_curve"]} for k, r in res.items()}),
        ev("compression", "zlib-compressed sizes (bits) of state vs transition sequence; proxy only.",
           {k: [r["zlib_bits_state"], r["zlib_bits_trans"]] for k, r in res.items()}),
    ]
    return {
        "deterministic": {"not_trace": {"states": det_states, "deltas": det_deltas}, "sources": res,
                          "bias_bound": bias},
        "nondeterministic": {"not_trace_wall_interval_ns_median": statistics.median(wall) if wall else None,
                             "note": "wall-clock intervals observe the Python instrument, not the model"},
        "checks": checks, "evidence": evidence,
    }
