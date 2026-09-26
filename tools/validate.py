"""Validate the research substrate. Exit status 1 on any violation.

Checks
  1. every evidence record passes the epistemic evidence guard
  2. every hypothesis / discovery passes the epistemic claim guard
  3. cross-references resolve (experiments, hypotheses, concepts, queue deps)
  4. run artifacts match their manifest hashes (integrity)
  5. the versioned provenance graph is acyclic and has no dangling references
  6. nomenclature term_class values are from the allowed set

    python3 -m tools.validate
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate import artifacts as A  # noqa: E402
from substrate.epistemic import STATUSES, check_claim, check_evidence_record  # noqa: E402
from substrate.ledger import RUNS, all_evidence, load_json, read_jsonl, run_index  # noqa: E402

TERM_CLASSES = {"ESTABLISHED_ACADEMIC_TERM", "INTERNAL_WORKING_TERM", "PROPOSED_TERM", "REJECTED_TERM"}


def validate():
    v = []
    evs = all_evidence()
    runs = run_index()
    for e in evs:
        v += check_evidence_record(e)
    hyps = load_json("hypotheses.json", [])
    discs = load_json("discoveries.json", [])
    for claim in hyps + discs:
        v += check_claim(claim, evs, runs)
    exps = {e["experiment_id"] for e in load_json("experiments.json", [])}
    hids = {h["id"] for h in hyps}
    concepts = load_json("nomenclature.json", [])
    cids = {c["id"] for c in concepts}
    for h in hyps:
        for x in h.get("related_experiments", []):
            if x not in exps:
                v.append("{}: unknown experiment {}".format(h["id"], x))
        for t in h.get("related_terms", []):
            if t not in cids:
                v.append("{}: unknown term {}".format(h["id"], t))
    for c in concepts:
        if c.get("term_class") not in TERM_CLASSES:
            v.append("{}: bad term_class {}".format(c["id"], c.get("term_class")))
        if c.get("status") not in STATUSES:
            v.append("{}: bad status {}".format(c["id"], c.get("status")))
        for r in c.get("related_concepts", []) + c.get("parent_concepts", []):
            if r not in cids:
                v.append("{}: unknown related concept {}".format(c["id"], r))
    queue = load_json("research_queue.json", [])
    qids = {q["task_id"] for q in queue}
    for q in queue:
        for d in q.get("dependency", []):
            if d not in qids:
                v.append("{}: unknown dependency {}".format(q["task_id"], d))
        for h in q.get("related_hypotheses", []):
            if h not in hids:
                v.append("{}: unknown hypothesis {}".format(q["task_id"], h))
    for e in load_json("experiments.json", []):
        for h in e.get("hypotheses", []):
            if h not in hids:
                v.append("{}: tests unknown hypothesis {}".format(e["experiment_id"], h))
    # artifact integrity
    for exp in sorted(os.listdir(RUNS)) if os.path.isdir(RUNS) else []:
        for rid in sorted(os.listdir(os.path.join(RUNS, exp))):
            d = os.path.join(RUNS, exp, rid)
            mp = os.path.join(d, "manifest.json")
            if not os.path.exists(mp):
                v.append("{}: missing manifest".format(d)); continue
            m = A.load(mp)
            for fn, h in m["files"].items():
                if A.sha256_file(os.path.join(d, fn)) != h:
                    v.append("{}/{}: hash mismatch (artifact modified after recording)".format(d, fn))
            if A.sha256_obj(A.load(os.path.join(d, "deterministic.json"))) != m["det_hash"]:
                v.append("{}: deterministic hash mismatch".format(d))
    # provenance
    from tools.provenance import analyse, build
    a = analyse(build(collapse=False))
    if not a["is_dag"]:
        v.append("provenance (versioned) has cycles: {}".format(a["nontrivial_sccs"][:3]))
    if a["dangling_references"]:
        v.append("provenance has dangling references: {}".format(a["dangling_references"]))
    return v


def main():
    v = validate()
    for x in v:
        print("VIOLATION:", x)
    print("{} violation(s)".format(len(v)))
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
