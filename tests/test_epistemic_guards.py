"""Validation of the validation system (charter §76).

Each test constructs a deliberately WRONG epistemic move and asserts that the
guard rejects it. If one of these tests fails, the harness can silently promote
an interpretation to evidence — treat that as a research-integrity bug.
"""

import unittest

from substrate.epistemic import check_claim, check_evidence_record

SIM = {"id": "EV-sim", "kind": "derived_measurement", "domain": "simulated", "status": "SIMULATED",
       "statement": "injected flips were corrected", "run_id": "RUN-1"}
COMP = {"id": "EV-comp", "kind": "derived_measurement", "domain": "computational", "status": "SIMULATED",
        "statement": "rule 90 damage annihilates", "run_id": "RUN-1"}
INTERP = {"id": "EV-int", "kind": "interpretation", "domain": "computational", "status": "INFERRED",
          "statement": "this suggests a universal law"}
LIT = {"id": "EV-lit", "kind": "external_source", "domain": "literature", "status": "LITERATURE_SUPPORTED",
       "statement": "JEDEC defines SEU", "source": "JEDEC JESD89"}
DERIV = {"id": "EV-drv", "kind": "derivation", "domain": "mathematical", "status": "DERIVED",
         "statement": "injective maps preserve distinctness"}
PHYS = {"id": "EV-phys", "kind": "raw_observation", "domain": "physical", "status": "OBSERVED",
        "statement": "beam test counted upsets"}
ALL = [SIM, COMP, INTERP, LIT, DERIV, PHYS]
RUNS = {"RUN-1": {"reproduced": True}, "RUN-2": {"reproduced": False}}


def claim(**kw):
    base = {"id": "H-T", "statement": "test claim", "subject_domain": "computational", "evidence": []}
    base.update(kw)
    return base


class TestWrongMovesAreRejected(unittest.TestCase):
    def assertRejected(self, c, evidence=ALL, runs=RUNS):
        self.assertTrue(check_claim(c, evidence, runs), "guard accepted a wrong claim: {}".format(c))

    def assertAccepted(self, c, evidence=ALL, runs=RUNS):
        self.assertEqual(check_claim(c, evidence, runs), [])

    # --- simulation must never become physical observation -------------------
    def test_simulated_flip_is_not_observed_physical_seu(self):
        self.assertRejected(claim(status="OBSERVED", subject_domain="physical", evidence=["EV-sim"]))

    def test_simulation_cannot_experimentally_support_physical_claim(self):
        self.assertRejected(claim(status="EXPERIMENTALLY_SUPPORTED", subject_domain="physical",
                                  evidence=["EV-sim"], falsification="x", falsification_checked=True))

    def test_simulated_evidence_labelled_observed(self):
        bad = dict(SIM, status="OBSERVED")
        self.assertTrue(check_evidence_record(bad))

    def test_model_execution_is_not_observed_even_for_model_claims(self):
        self.assertRejected(claim(status="OBSERVED", evidence=["EV-comp"]))

    # --- interpretation must not become evidence -------------------------------
    def test_interpretation_alone_cannot_support(self):
        for st in ("ESTABLISHED", "EXPERIMENTALLY_SUPPORTED", "INFERRED", "SIMULATED", "DERIVED"):
            self.assertRejected(claim(status=st, evidence=["EV-int"], falsification="x", falsification_checked=True))

    def test_interpretation_record_with_strong_status(self):
        self.assertTrue(check_evidence_record(dict(INTERP, status="EXPERIMENTALLY_SUPPORTED")))

    # --- hypotheses cannot silently become facts --------------------------------
    def test_established_needs_source_or_derivation(self):
        self.assertRejected(claim(status="ESTABLISHED", evidence=["EV-comp"]))

    def test_derived_needs_derivation(self):
        self.assertRejected(claim(status="DERIVED", evidence=["EV-comp"]))

    def test_experimentally_supported_needs_falsification_checked(self):
        self.assertRejected(claim(status="EXPERIMENTALLY_SUPPORTED", evidence=["EV-comp"], falsification="x"))
        self.assertRejected(claim(status="EXPERIMENTALLY_SUPPORTED", evidence=["EV-comp"], falsification_checked=True))

    def test_experimentally_supported_needs_reproduced_run(self):
        ev2 = dict(COMP, id="EV-c2", run_id="RUN-2")
        self.assertRejected(claim(status="EXPERIMENTALLY_SUPPORTED", evidence=["EV-c2"],
                                  falsification="x", falsification_checked=True), evidence=ALL + [ev2])

    def test_missing_evidence_reference(self):
        self.assertRejected(claim(status="SIMULATED", evidence=["EV-does-not-exist"]))

    def test_unknown_status_proven(self):
        self.assertRejected(claim(status="PROVEN", evidence=["EV-comp"]))

    def test_proven_language_in_empirical_claim(self):
        self.assertRejected(claim(status="SIMULATED", evidence=["EV-comp"], statement="we have proven the law"))

    def test_provenance_is_not_proven(self):
        # regression for F-009: substring match flagged the word "provenance"
        self.assertAccepted(claim(status="HYPOTHESIS", statement="the provenance graph is acyclic"))

    def test_novelty_needs_scope(self):
        self.assertRejected(claim(status="HYPOTHESIS", statement="a novel computational object"))
        self.assertAccepted(claim(status="HYPOTHESIS", statement="a novel computational object", novelty_scope="repository"))

    def test_external_source_needs_source(self):
        self.assertTrue(check_evidence_record(dict(LIT, source="")))

    def test_computational_measurement_needs_run(self):
        self.assertTrue(check_evidence_record({k: v for k, v in COMP.items() if k != "run_id"}))

    # --- correct moves are accepted (the guard must not block legitimate research)
    def test_legitimate_moves(self):
        self.assertAccepted(claim(status="HYPOTHESIS"))
        self.assertAccepted(claim(status="UNRESOLVED"))
        self.assertAccepted(claim(status="SIMULATED", evidence=["EV-comp"]))
        self.assertAccepted(claim(status="DERIVED", subject_domain="mathematical", evidence=["EV-drv"]))
        self.assertAccepted(claim(status="EXPERIMENTALLY_SUPPORTED", evidence=["EV-comp"],
                                  falsification="x", falsification_checked=True))
        self.assertAccepted(claim(status="OBSERVED", subject_domain="physical", evidence=["EV-phys"]))
        self.assertAccepted(claim(status="LITERATURE_SUPPORTED", subject_domain="physical", evidence=["EV-lit"]))

    def test_strange_hypothesis_not_rejected_for_strangeness(self):
        # §54: the harness must not reject a hypothesis for sounding strange.
        self.assertAccepted(claim(status="HYPOTHESIS", statement="transformations of transformations have their own anomalies"))


if __name__ == "__main__":
    unittest.main()
