"""Registered experiments. Each module defines SPEC, CONFIG and run(config).

run(config) returns:
  deterministic     JSON-able results that must reproduce bit-identically
  nondeterministic  instrument observations (wall-clock) — never hashed
  checks            list of {id, description, passed, value}: pre-registered
                    predictions / falsification conditions, evaluated in code
  evidence          evidence records for the ledger (see substrate.epistemic)
"""


def check(cid, description, passed, value=None):
    return {"id": cid, "description": description, "passed": bool(passed), "value": value}


def ev(key, statement, value, status="SIMULATED", kind="derived_measurement", domain="computational", **extra):
    d = {"key": key, "statement": statement, "value": value, "status": status, "kind": kind, "domain": domain}
    d.update(extra)
    return d
