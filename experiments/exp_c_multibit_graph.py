"""EXP-C — multi-bit transition graphs.

Two parts:
  C1  structural census of functional graphs for several map families on
      X_n, n = 8 (256 states) — and injectivity of ECA rules for n = 4..12.
  C2  instrument calibration: random mappings on n = 4096 states against the
      asymptotic results of Flajolet & Odlyzko (1990):
        E[#cyclic nodes]      ~ sqrt(pi n / 2)
        E[tail length]        ~ sqrt(pi n / 8)   (mean over vertices)
        E[#components]        ~ (1/2) ln n       (leading order only)
      Agreement is a test of the *instrument*, not of the research premise.
"""

import math
import random

from substrate.core import eca, increment, random_map, random_permutation
from substrate.graph import functional_graph_analysis, public
from . import check, ev

SPEC = {
    "experiment_id": "EXP-C",
    "title": "Multi-bit transition graph",
    "question": "What structure do transition graphs of multi-bit deterministic maps have, and does the instrument reproduce known random-mapping statistics?",
    "hypotheses": ["H-004", "H-007"],
    "objective": "Census of functional-graph structure across map families; calibrate graph analysis against established asymptotics.",
    "model": "increment, ECA rules, random maps and permutations on n-bit state spaces.",
    "procedure": "Tabulate maps, run functional_graph_analysis; for calibration average over seeds.",
    "expected_result": "Bijective maps have no Garden-of-Eden states and no transients. Random-map means within 10% of sqrt(pi n/2) (cyclic) and sqrt(pi n/8) (tail).",
    "falsification_condition": "Relative error > 10% on cyclic-node or tail-length means; any bijective map with a transient.",
    "epistemic_status_of_result": "SIMULATED; calibration compared against LITERATURE_SUPPORTED values.",
}

CONFIG = {"seed": 1729, "n_bits": 8, "eca_rules": [0, 15, 30, 51, 90, 110, 150, 170, 184, 204, 232],
          "injectivity_sizes": [4, 5, 6, 7, 8, 9, 10, 11, 12], "calib_bits": 12, "calib_samples": 200}


def run(config):
    n = config["n_bits"]
    rng = random.Random(config["seed"])
    census = {}
    maps = [increment(n)] + [eca(r, n) for r in config["eca_rules"]] + \
           [random_map(n, rng.randrange(1 << 30)) for _ in range(3)] + [random_permutation(n, rng.randrange(1 << 30))]
    for i, f in enumerate(maps):
        key = f.name if f.name.startswith(("increment", "eca")) else "{}#{}".format(f.name, i)
        a = public(functional_graph_analysis(f.table))
        a.pop("basin_sizes")
        a["cycle_length_multiset_size"] = len(a["cycle_lengths"])
        if len(a["cycle_lengths"]) > 20:
            a["cycle_lengths"] = a["cycle_lengths"][:10] + ["..."] + a["cycle_lengths"][-10:]
        census[key] = a

    inj = {}
    for r in config["eca_rules"]:
        inj[str(r)] = {str(m): eca(r, m).is_injective() for m in config["injectivity_sizes"]}

    N = 1 << config["calib_bits"]
    samples = []
    for _ in range(config["calib_samples"]):
        a = functional_graph_analysis(random_map(config["calib_bits"], rng.randrange(1 << 30)).table)
        samples.append((a["n_cyclic"], a["mean_tail"], a["n_components"]))
    m = [sum(s[i] for s in samples) / len(samples) for i in range(3)]
    theory = {"cyclic": math.sqrt(math.pi * N / 2), "tail": math.sqrt(math.pi * N / 8), "components_leading": 0.5 * math.log(N)}
    rel = {"cyclic": m[0] / theory["cyclic"] - 1, "tail": m[1] / theory["tail"] - 1,
           "components_leading": m[2] / theory["components_leading"] - 1}
    calib = {"n_states": N, "samples": len(samples),
             "mean": {"cyclic": round(m[0], 6), "tail": round(m[1], 6), "components": round(m[2], 6)},
             "theory": {k: round(v, 6) for k, v in theory.items()},
             "relative_error": {k: round(v, 6) for k, v in rel.items()}}

    bij = [k for k, a in census.items() if a["injective"]]
    checks = [
        check("C1", "every injective map has no transients and no Garden-of-Eden states",
              all(census[k]["max_tail"] == 0 and census[k]["n_garden_of_eden"] == 0 for k in bij), bij),
        check("C2", "every non-injective map has at least one Garden-of-Eden state (pigeonhole)",
              all(a["n_garden_of_eden"] > 0 for a in census.values() if not a["injective"])),
        check("C3", "calibration: mean cyclic nodes within 10% of sqrt(pi n/2)", abs(rel["cyclic"]) < 0.10, rel["cyclic"]),
        check("C4", "calibration: mean tail length within 10% of sqrt(pi n/8)", abs(rel["tail"]) < 0.10, rel["tail"]),
        check("C5", "increment is a single cycle through all states", census["increment"]["cycle_lengths"] == [1 << n]),
    ]
    evidence = [
        ev("census", "Functional-graph census of map families on 8-bit state space.",
           {k: {f: a[f] for f in ("n_components", "n_cyclic", "max_tail", "n_garden_of_eden", "injective")} for k, a in census.items()}),
        ev("eca_injectivity", "Injectivity of ECA rules on rings of size 4..12 (exact, by tabulation).", inj),
        ev("calibration", "Random-mapping statistics vs Flajolet-Odlyzko asymptotics (n=4096, 200 maps).", calib),
    ]
    return {"deterministic": {"census": census, "eca_injectivity": inj, "calibration": calib},
            "nondeterministic": {}, "checks": checks, "evidence": evidence}
