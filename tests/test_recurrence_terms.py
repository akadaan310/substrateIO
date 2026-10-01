"""Nomenclature verification (bridge STASIS-3, phase 2): C-011 'attractor (periodic orbit)' in
substrateIO vs 'closed class' (bottom SCC) in purl NOMENCLATURE.md, which rejects 'attractor'.

Claim (DERIVED, standard): in a FUNCTIONAL graph (out-degree exactly 1) the following sets coincide:
  cycles of f  =  bottom (closed) strongly connected components  =  sets of recurrent states,
so 'attractor (periodic orbit)' and 'closed class' name the same objects there.
In a general (empirical, possibly nondeterministic) transition graph they do NOT coincide: a closed
class may contain several cycles, and a cycle need not be closed. The test checks both directions.
"""

import itertools
import random
import unittest

from substrate.graph import Digraph, functional_graph_analysis


def bottom_sccs(nodes, edges):
    g = Digraph()
    for v in nodes:
        g.add_node(str(v))
    for u, v in edges:
        g.add_edge(str(u), str(v))
    comps = [set(c) for c in g.scc()]
    out = []
    for c in comps:
        closed = all(str(v) in c for u, v in edges if str(u) in c)
        nontrivial = len(c) > 1 or any(str(u) == str(v) and str(u) in c for u, v in edges)
        if closed and nontrivial:
            out.append(frozenset(c))
    return set(out)


def recurrent_states(nodes, edges):
    succ = {v: set() for v in nodes}
    for u, v in edges:
        succ[u].add(v)
    rec = set()
    for s in nodes:
        seen, stack = set(), list(succ[s])
        while stack:
            x = stack.pop()
            if x in seen:
                continue
            seen.add(x)
            stack.extend(succ[x])
        if s in seen:  # s reaches itself
            # recurrent in the Markov sense also needs: every state reachable from s reaches s back
            if all(s in _reach(succ, y) | {y} if y != s else True for y in seen):
                rec.add(s)
    return rec


def _reach(succ, s):
    seen, stack = set(), list(succ[s])
    while stack:
        x = stack.pop()
        if x not in seen:
            seen.add(x)
            stack.extend(succ[x])
    return seen


class TestFunctionalGraphs(unittest.TestCase):
    def check_table(self, t):
        nodes = list(range(len(t)))
        edges = [(x, t[x]) for x in nodes]
        cycles = {frozenset(str(v) for v in c) for c in functional_graph_analysis(t)["_cycles"]}
        self.assertEqual(cycles, bottom_sccs(nodes, edges))
        cyc_nodes = {int(v) for c in cycles for v in c}
        self.assertEqual(cyc_nodes, recurrent_states(nodes, edges))

    def test_all_maps_on_4_states(self):
        # exhaustive: every f: X_2 -> X_2 (4^4 = 256 maps)
        for t in itertools.product(range(4), repeat=4):
            self.check_table(list(t))

    def test_random_maps(self):
        rng = random.Random(20261001)
        for _ in range(300):
            n = rng.randint(1, 7)
            self.check_table([rng.randrange(1 << n) for _ in range(1 << n)])


class TestEmpiricalGraphs(unittest.TestCase):
    def test_a_closed_class_can_contain_several_cycles(self):
        # a <-> b, a -> a : one closed class {a, b}, two distinct cycles (a), (a b)
        nodes, edges = ["a", "b"], [("a", "b"), ("b", "a"), ("a", "a")]
        self.assertEqual(bottom_sccs(nodes, edges), {frozenset({"a", "b"})})

    def test_a_cycle_need_not_be_closed(self):
        # a <-> b, b -> c (absorbing): the cycle (a b) is not a closed class; only {c} is
        nodes, edges = ["a", "b", "c"], [("a", "b"), ("b", "a"), ("b", "c"), ("c", "c")]
        self.assertEqual(bottom_sccs(nodes, edges), {frozenset({"c"})})
        self.assertEqual(recurrent_states(nodes, edges), {"c"})


if __name__ == "__main__":
    unittest.main()
