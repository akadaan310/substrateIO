"""Epistemic statuses and the rules that stop a claim from being promoted
beyond its evidence.

The authoritative human-readable definitions live in
research/registries/epistemic_statuses.json; this module encodes the
*machine-checkable* part of them. `check_claim` returns a list of violations;
an empty list means "no rule violated", NOT "the claim is true".

Evidence kinds (charter §42):
  raw_observation, derived_measurement, interpretation, external_source,
  inference, hypothesis, derivation

Evidence domains — what the evidence was produced *from*:
  mathematical   a derivation/proof over formal objects
  computational  execution of a computational model where the model itself is
                 the subject of the claim
  simulated      execution of a model that *stands in for* another target
                 (e.g. injected bit flips standing in for physical upsets)
  physical       measurement of physical hardware / the physical world
  repository     measurement of this repository's own recorded history
  literature     an external published source

Claim subject domains: mathematical | computational | physical | repository | research_process
"""

from __future__ import annotations

import re
from typing import Dict, List, Sequence

STATUSES = [
    "AXIOM", "ESTABLISHED", "DERIVED", "OBSERVED", "SIMULATED",
    "EXPERIMENTALLY_SUPPORTED", "LITERATURE_SUPPORTED", "INFERRED",
    "PROVISIONAL", "HYPOTHESIS", "UNRESOLVED", "DISPROVEN", "REJECTED",
]

EVIDENCE_KINDS = ["raw_observation", "derived_measurement", "interpretation",
                  "external_source", "inference", "hypothesis", "derivation"]

EVIDENCE_DOMAINS = ["mathematical", "computational", "simulated", "physical",
                    "repository", "literature"]

SUBJECT_DOMAINS = ["mathematical", "computational", "physical", "repository", "research_process"]

# Whole-word match: a substring match flagged "provenance" (failure F-009).
FORBIDDEN_RE = re.compile(r"\b(proven|proved|proof that)\b")

NOVELTY_SCOPES = ["repository", "team", "literature_unsearched", "literature_searched"]


def _ev_by_id(evidence: Sequence[dict]) -> Dict[str, dict]:
    return {e["id"]: e for e in evidence}


def check_claim(claim: dict, evidence: Sequence[dict], runs: Dict[str, dict] = None) -> List[str]:
    """Validate one claim (hypothesis, discovery, or state-summary item).

    claim fields used: id, status, subject_domain, evidence (list of ids),
    statement, novelty_scope (if the text claims novelty), falsification
    (for EXPERIMENTALLY_SUPPORTED), falsification_checked.
    """
    v: List[str] = []
    cid = claim.get("id", "?")
    st = claim.get("status")
    if st not in STATUSES:
        return ["{}: unknown status {!r}".format(cid, st)]
    subj = claim.get("subject_domain")
    if subj not in SUBJECT_DOMAINS:
        v.append("{}: unknown subject_domain {!r}".format(cid, subj))
    evmap = _ev_by_id(evidence)
    refs = claim.get("evidence", [])
    missing = [r for r in refs if r not in evmap]
    if missing:
        v.append("{}: references missing evidence {}".format(cid, missing))
    evs = [evmap[r] for r in refs if r in evmap]
    kinds = {e["kind"] for e in evs}
    domains = {e["domain"] for e in evs}
    # evidence that can support anything at all (interpretations & hypotheses cannot)
    substantive = [e for e in evs if e["kind"] not in ("interpretation", "hypothesis")]

    text = (claim.get("statement", "") + " " + claim.get("summary", "")).lower()
    if "novel" in text and claim.get("novelty_scope") not in NOVELTY_SCOPES:
        v.append("{}: mentions novelty without a novelty_scope in {}".format(cid, NOVELTY_SCOPES))
    if subj != "mathematical" and FORBIDDEN_RE.search(text):
        v.append("{}: empirical claim uses 'proven' language".format(cid))

    needs_support = {"ESTABLISHED", "DERIVED", "OBSERVED", "SIMULATED",
                     "EXPERIMENTALLY_SUPPORTED", "LITERATURE_SUPPORTED", "INFERRED",
                     "DISPROVEN"}
    if st in needs_support and not substantive:
        v.append("{}: status {} requires non-interpretive evidence; has kinds {}".format(cid, st, sorted(kinds)))

    if st == "ESTABLISHED" and not ({"external_source", "derivation"} & kinds):
        v.append("{}: ESTABLISHED requires an external_source or derivation".format(cid))
    if st == "DERIVED" and "derivation" not in kinds:
        v.append("{}: DERIVED requires a derivation evidence record".format(cid))
    if st == "LITERATURE_SUPPORTED" and "external_source" not in kinds:
        v.append("{}: LITERATURE_SUPPORTED requires an external_source".format(cid))
    if st == "OBSERVED":
        # Executing a model yields SIMULATED results, even when the model is the
        # subject; OBSERVED is reserved for things that exist independently of
        # the instrument (hardware, this repository's recorded history).
        if not ({"physical", "repository"} & domains):
            v.append("{}: OBSERVED requires physical or repository evidence".format(cid))
        if subj == "physical" and "physical" not in domains:
            v.append("{}: OBSERVED physical claim without physical evidence".format(cid))
    if st == "SIMULATED" and not ({"simulated", "computational"} & domains):
        v.append("{}: SIMULATED requires simulated/computational evidence".format(cid))

    # The central guard: simulation never becomes physical evidence.
    if subj == "physical" and st in {"OBSERVED", "EXPERIMENTALLY_SUPPORTED", "ESTABLISHED"}:
        if "physical" not in domains and not (st == "ESTABLISHED" and "literature" in domains):
            v.append("{}: physical claim at {} supported only by {}".format(cid, st, sorted(domains)))

    if st == "EXPERIMENTALLY_SUPPORTED":
        if not claim.get("falsification"):
            v.append("{}: EXPERIMENTALLY_SUPPORTED requires a stated falsification condition".format(cid))
        if claim.get("falsification_checked") is not True:
            v.append("{}: falsification condition was not checked".format(cid))
        run_ids = [e.get("run_id") for e in evs if e.get("run_id")]
        if not run_ids:
            v.append("{}: EXPERIMENTALLY_SUPPORTED requires evidence from a recorded run".format(cid))
        if runs is not None:
            for r in run_ids:
                if r not in runs:
                    v.append("{}: cites unknown run {}".format(cid, r))
                elif not runs[r].get("reproduced"):
                    v.append("{}: run {} has not been reproduced".format(cid, r))
    if st == "DISPROVEN" and not claim.get("contradicting_evidence") and not claim.get("falsification_checked"):
        v.append("{}: DISPROVEN requires contradicting evidence or a triggered falsification".format(cid))
    return v


def check_evidence_record(e: dict) -> List[str]:
    v = []
    for f in ("id", "kind", "domain", "statement", "status"):
        if f not in e:
            v.append("{}: evidence missing field {}".format(e.get("id", "?"), f))
    if e.get("kind") not in EVIDENCE_KINDS:
        v.append("{}: unknown evidence kind {!r}".format(e.get("id"), e.get("kind")))
    if e.get("domain") not in EVIDENCE_DOMAINS:
        v.append("{}: unknown evidence domain {!r}".format(e.get("id"), e.get("domain")))
    if e.get("status") not in STATUSES:
        v.append("{}: unknown status {!r}".format(e.get("id"), e.get("status")))
    # An interpretation cannot carry a status stronger than INFERRED.
    if e.get("kind") == "interpretation" and e.get("status") not in {"INFERRED", "PROVISIONAL", "HYPOTHESIS", "UNRESOLVED", "REJECTED"}:
        v.append("{}: interpretation carries status {}".format(e.get("id"), e.get("status")))
    # Model executions cannot be labelled OBSERVED.
    if e.get("domain") in ("simulated", "computational") and e.get("status") == "OBSERVED":
        v.append("{}: model-execution evidence labelled OBSERVED".format(e.get("id")))
    if e.get("kind") == "external_source" and not e.get("source"):
        v.append("{}: external_source without a source".format(e.get("id")))
    if e.get("kind") in ("raw_observation", "derived_measurement") and e.get("domain") in ("computational", "simulated") and not e.get("run_id"):
        v.append("{}: computational measurement without run_id".format(e.get("id")))
    return v
