"""Unit tests for the computational instruments. Run: python3 -m unittest discover -s tests"""

import itertools
import math
import random
import unittest

from substrate.core import StateSpace, eca, eca_step, increment, one_bit_maps, random_map
from substrate.graph import Digraph, functional_graph_analysis
from substrate.info import conditional_entropy_next, entropy, mutual_information_pairs
from substrate.layers import CODES, Hamming74, SECDED84, ham74_encode
from substrate.perturb import Intervention, compare_state_sequences
from substrate.projection import (coarsest_congruence, compatibility, from_transitions,
                                  information_loss, to_transitions)
from substrate.trace import run, step_states


class TestCore(unittest.TestCase):
    def test_bits_roundtrip(self):
        X = StateSpace(5)
        for x in X.states():
            self.assertEqual(X.from_bits(X.to_bits(x)), x)

    def test_one_bit_maps_complete(self):
        self.assertEqual(sorted(tuple(m.table) for m in one_bit_maps()),
                         sorted(itertools.product((0, 1), repeat=2)))

    def test_eca_table_matches_step(self):
        for rule in (30, 90, 110):
            f = eca(rule, 7)
            for x in range(128):
                self.assertEqual(f(x), eca_step(rule, 7, x))

    def test_eca_identity_and_shift(self):
        self.assertEqual(eca(204, 6).table, list(range(64)))
        self.assertTrue(eca(170, 6).is_injective())


class TestGraph(unittest.TestCase):
    def test_functional_graph_invariants(self):
        for seed in range(5):
            f = random_map(7, seed)
            a = functional_graph_analysis(f.table)
            self.assertEqual(sum(a["basin_sizes"]), 128)
            self.assertEqual(sum(a["cycle_lengths"]), a["n_cyclic"])
            self.assertEqual(a["n_components"], len(a["cycle_lengths"]))
            for x in range(128):  # following tail[x] steps lands on a cycle
                y = x
                for _ in range(a["_tail"][x]):
                    y = f(y)
                self.assertEqual(a["_tail"][y], 0)

    def test_increment_single_cycle(self):
        a = functional_graph_analysis(increment(6).table)
        self.assertEqual(a["cycle_lengths"], [64])

    def test_scc_and_dag(self):
        g = Digraph()
        for u, v in [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d")]:
            g.add_edge(u, v)
        self.assertFalse(g.is_dag())
        self.assertIn(sorted(["a", "b", "c"]), [sorted(c) for c in g.scc()])
        h = Digraph()
        for u, v in [("a", "b"), ("b", "c"), ("a", "c")]:
            h.add_edge(u, v)
        self.assertTrue(h.is_dag())
        self.assertEqual(h.longest_path_length(), 2)


class TestTraceAndPerturb(unittest.TestCase):
    def test_intervention_is_recorded_as_event(self):
        f = eca(204, 4)
        tr = run(f, 4, 0, 5, {2: Intervention("state_bit_flip", 2, {"bit": 1}).state_fn()}, clock=False)
        labels = [e.label for e in tr.events]
        self.assertEqual(labels.count("intervention"), 1)
        self.assertEqual(step_states(tr), [0, 0, 2, 2, 2, 2])

    def test_classes(self):
        n = 8
        base = [0] * 6
        self.assertEqual(compare_state_sequences(base, [0, 1, 0, 0, 0, 0], 1, n, [0])["class"], "masked")
        self.assertEqual(compare_state_sequences(base, [0, 1, 1, 0, 0, 0], 1, n, [0])["class"], "recovered")
        self.assertEqual(compare_state_sequences(base, [0, 1, 3, 7, 7, 7], 1, n, [0])["class"], "amplified")
        self.assertEqual(compare_state_sequences(base, [0, 1, 1, 1, 1, 1], 1, n, [0])["class"], "persistent_local")
        self.assertEqual(compare_state_sequences(base, [0, 1, 2, 4, 8, 16], 1, n, [0])["class"], "transformed")
        self.assertEqual(compare_state_sequences(base, base, 1, n, [])["class"], "null")

    def test_injective_never_masks(self):
        f = eca(150, 7)  # injective for n not divisible by 3
        self.assertTrue(f.is_injective())
        for x0 in range(0, 128, 9):
            b = step_states(run(f, 7, x0, 20, clock=False))
            for i in range(7):
                p = step_states(run(f, 7, x0, 20, {3: Intervention("state_bit_flip", 3, {"bit": i}).state_fn()}, clock=False))
                self.assertNotIn(compare_state_sequences(b, p, 3, 7, [i])["class"], ("masked", "recovered"))


class TestInfoAndProjection(unittest.TestCase):
    def test_entropy_basics(self):
        self.assertAlmostEqual(entropy([0, 1, 0, 1]), 1.0)
        self.assertEqual(entropy([1, 1, 1]), 0.0)
        self.assertAlmostEqual(mutual_information_pairs([(0, 0), (1, 1)] * 10), 1.0)

    def test_deterministic_sequence_zero_conditional_entropy(self):
        xs = [0, 1] * 100
        self.assertAlmostEqual(conditional_entropy_next(xs, 1), 0.0)

    def test_information_loss_identity_constant(self):
        X = list(range(16))
        self.assertEqual(information_loss(X, lambda x: x)["H_X_given_PX"], 0.0)
        self.assertAlmostEqual(information_loss(X, lambda x: 0)["H_X_given_PX"], 4.0)

    def test_transition_roundtrip(self):
        rng = random.Random(1)
        xs = [rng.randrange(2) for _ in range(50)]
        self.assertEqual(from_transitions(xs[0], to_transitions(xs)), xs)
        comp = [1 - x for x in xs]
        self.assertEqual(to_transitions(xs), to_transitions(comp))

    def test_compatibility_and_congruence(self):
        f = increment(4)
        self.assertTrue(compatibility(f.table, lambda x: x & 3)["compatible"])
        self.assertFalse(compatibility(f.table, lambda x: x >> 2)["compatible"])
        blocks = coarsest_congruence(f.table, lambda x: x & 1)
        self.assertEqual(len(set(blocks)), 2)
        # congruence property holds for the result
        for x in range(16):
            for y in range(16):
                if blocks[x] == blocks[y]:
                    self.assertEqual(blocks[f(x)], blocks[f(y)])


class TestCodes(unittest.TestCase):
    def test_all_codes_roundtrip(self):
        for code in CODES.values():
            for d in range(16):
                dec = code.decode(code.encode(d))
                self.assertEqual((dec.value, dec.status), (d, "ok"))

    def test_hamming_min_distance_3(self):
        cw = [ham74_encode(d) for d in range(16)]
        dmin = min(bin(a ^ b).count("1") for a, b in itertools.combinations(cw, 2))
        self.assertEqual(dmin, 3)

    def test_secded_detects_all_doubles(self):
        c = SECDED84()
        for d in range(16):
            for i, j in itertools.combinations(range(8), 2):
                self.assertEqual(c.decode(c.encode(d) ^ (1 << i) ^ (1 << j)).status, "detected")

    def test_hamming_corrects_all_singles(self):
        c = Hamming74()
        for d in range(16):
            for i in range(7):
                dec = c.decode(c.encode(d) ^ (1 << i))
                self.assertEqual((dec.value, dec.located_bit), (d, i))


if __name__ == "__main__":
    unittest.main()
