"""Generate the machine-readable current-state and handoff artifacts from the
registries, so they cannot drift from the source of truth.

    python3 -m tools.snapshot
"""

import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from substrate import artifacts as A  # noqa: E402
from substrate.ledger import all_evidence, load_json, read_jsonl, run_index  # noqa: E402

OUT = os.path.join(A.ROOT, "research", "state")


def main():
    hyps = load_json("hypotheses.json", [])
    exps = load_json("experiments.json", [])
    evs = all_evidence()
    runs = run_index()
    states = read_jsonl("research_states.jsonl")
    onto = [o for o in read_jsonl("ontology_history.jsonl") if o["type"] == "ontology_version"]
    execs = read_jsonl("executions.jsonl")
    last_exec = {}
    for e in execs:
        last_exec[e["run_id"]] = e
    by_status = defaultdict(list)
    for h in hyps:
        by_status[h["status"]].append(h["id"])
    ev_by_status = defaultdict(list)
    for e in evs:
        ev_by_status[e["status"]].append(e["id"])

    current = {
        "research_state": states[-1]["id"],
        "research_state_summary": states[-1]["summary"],
        "lineage": [s["id"] for s in states],
        "research_question": "When computation is observed as state transitions across multiple representational spaces, what structure exists in the transformations between those spaces, and can that structure itself become an object of computation, measurement, verification, and discovery? (open)",
        "ontology_version": onto[-1]["id"],
        "ontology_summary": onto[-1]["summary"],
        "nomenclature_count": len(load_json("nomenclature.json", [])),
        "hypotheses": {h["id"]: {"status": h["status"], "statement": h["statement"]} for h in hyps},
        "hypotheses_by_status": dict(sorted(by_status.items())),
        "experiments": {e["experiment_id"]: {
            "title": e["title"],
            "runs": [{"run_id": r["run_id"], "reproduced": r["reproduced"], "executions": r["executions"],
                      "checks_passed_last": last_exec.get(r["run_id"], {}).get("checks_passed")} for r in e["runs"]],
            "post_hoc_checks": e.get("post_hoc_checks", [])} for e in exps},
        "evidence_by_status": dict(sorted(ev_by_status.items())),
        "failures": [{"id": f["id"], "type": f["type"], "status": f["status"]} for f in load_json("failures.json", [])],
        "discoveries": [{"id": d["id"], "stage": d["stage"], "status": d["status"]} for d in load_json("discoveries.json", [])],
        "open_problems": [o["id"] for o in load_json("open_problems.json", [])],
        "queue_ready": [q["task_id"] for q in load_json("research_queue.json", []) if q["status"] == "ready"],
        "implementation": {"language": "Python 3.11 stdlib only", "packages": ["substrate", "experiments", "tools", "tests"],
                           "entry_points": ["python3 -m experiments.run_all", "python3 -m tools.validate",
                                            "python3 -m tools.provenance", "python3 -m tools.snapshot",
                                            "python3 -m unittest discover -s tests -t ."]},
        "known_limitations": [
            "all results concern models; no physical observation",
            "tiny models (<=16-bit state, 8-step program)",
            "plug-in entropy estimators",
            "several literature entries unverified (Q-011)",
            "post-hoc checks are exploratory",
            "cross-layer normalised distances are ad hoc (OP-006)",
            "wall-clock timings measure the interpreter, not the models"],
        "human_readable": "research/state/CURRENT_STATE.md",
    }
    A.dump(os.path.join(OUT, "current_state.json"), current)

    def ids(pred):
        return sorted(e["id"] for e in evs if pred(e))

    handoff = {
        "from_research_state": states[-1]["id"],
        "bootstrap": "PROTOCOL.md",
        "WHAT_WE_KNOW": {"derived": ids(lambda e: e["kind"] == "derivation"),
                          "established_hypotheses": by_status.get("ESTABLISHED", []) + by_status.get("DERIVED", [])},
        "WHAT_WE_THINK": {"interpretations": ids(lambda e: e["kind"] == "interpretation"),
                          "provisional_ontology": onto[-1]["id"]},
        "WHAT_WE_OBSERVED": {"evidence": ids(lambda e: e["status"] == "OBSERVED"),
                             "note": "repository-domain only; nothing physical"},
        "WHAT_WE_SIMULATED": {"runs": sorted(runs), "evidence": ids(lambda e: e["status"] == "SIMULATED"),
                              "experimentally_supported_model_scope": by_status.get("EXPERIMENTALLY_SUPPORTED", []),
                              "simulated_only": by_status.get("SIMULATED", [])},
        "WHAT_WE_DONT_KNOW": {"unresolved_hypotheses": by_status.get("UNRESOLVED", []),
                              "open_problems": current["open_problems"]},
        "WHAT_FAILED": {"failures": [f["id"] for f in current["failures"]],
                        "disproven": by_status.get("DISPROVEN", []), "rejected": by_status.get("REJECTED", [])},
        "WHAT_CHANGED": [{"state": s["id"], "parent": s["parent"], "operation": s["operation"]} for s in states],
        "WHAT_SHOULD_HAPPEN_NEXT": [{"task_id": q["task_id"], "question": q["question"], "dependency": q["dependency"], "status": q["status"]}
                                    for q in load_json("research_queue.json", [])],
        "human_readable": "research/state/HANDOFF.md",
    }
    A.dump(os.path.join(OUT, "handoff.json"), handoff)
    print("wrote current_state.json, handoff.json for", states[-1]["id"])


if __name__ == "__main__":
    main()
