"""Transition graphs.

For a deterministic map f on a finite set, the transition graph G_f = (X, {(x, f(x))})
is a *functional graph* (every vertex has out-degree 1). Its established
structure (e.g. Flajolet & Odlyzko 1990): each weakly connected component
contains exactly one cycle; every other vertex lies on a tree feeding the cycle.

Vocabulary mapping (see nomenclature):
  cycle            = attractor (periodic orbit) of the discrete dynamical system
  component        = basin of that attractor
  tail length      = transient length (rho-length minus cycle length)
  in-degree 0      = "Garden-of-Eden" state (Moore 1962 terminology, for CA)

A general `Digraph` with iterative Tarjan SCC is provided for non-functional
graphs (labelled transition systems, the provenance graph, ...).
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Sequence, Tuple


def functional_graph_analysis(table: Sequence[int]) -> dict:
    """Exact structural analysis of the functional graph of `table`.

    Returns cycles, per-vertex component id, tail (transient) length, basin
    sizes and summary statistics. O(|X|)."""
    n = len(table)
    comp = [-1] * n      # component (== attractor) id
    tail = [-1] * n      # steps until reaching the cycle
    on_cycle = [False] * n
    cycles: List[List[int]] = []
    state = [0] * n      # 0 unvisited, 1 on current path, 2 done

    for start in range(n):
        if state[start]:
            continue
        path = []
        x = start
        while state[x] == 0:
            state[x] = 1
            path.append(x)
            x = table[x]
        if state[x] == 1:  # new cycle found: x is on it
            idx = path.index(x)
            cyc = path[idx:]
            cid = len(cycles)
            cycles.append(cyc)
            for v in cyc:
                on_cycle[v] = True
                comp[v] = cid
                tail[v] = 0
                state[v] = 2
            path = path[:idx]
        # unwind remaining path (tree vertices) in reverse
        for v in reversed(path):
            nxt = table[v]
            comp[v] = comp[nxt]
            tail[v] = tail[nxt] + 1
            state[v] = 2

    indeg = Counter(table)
    basin = Counter(comp)
    return {
        "n_states": n,
        "n_components": len(cycles),
        "cycle_lengths": sorted(len(c) for c in cycles),
        "n_cyclic": sum(on_cycle),
        "basin_sizes": sorted(basin.values(), reverse=True),
        "max_tail": max(tail) if n else 0,
        "mean_tail": (sum(tail) / n) if n else 0.0,
        "n_garden_of_eden": sum(1 for x in range(n) if indeg[x] == 0),
        "n_fixed_points": sum(1 for x in range(n) if table[x] == x),
        "injective": len(indeg) == n,
        "max_indegree": max(indeg.values()) if n else 0,
        # per-vertex data (kept for comparison; callers may drop it)
        "_comp": comp,
        "_tail": tail,
        "_cycles": cycles,
    }


def public(analysis: dict) -> dict:
    """Drop per-vertex arrays for compact storage."""
    return {k: v for k, v in analysis.items() if not k.startswith("_")}


def edges_of(table: Sequence[int]) -> List[Tuple[int, int]]:
    return [(x, y) for x, y in enumerate(table)]


class Digraph:
    def __init__(self) -> None:
        self.adj: Dict[str, List[str]] = defaultdict(list)
        self.nodes: Dict[str, dict] = {}

    def add_node(self, v: str, **attrs) -> None:
        self.nodes.setdefault(v, {}).update(attrs)
        self.adj.setdefault(v, [])

    def add_edge(self, u: str, v: str) -> None:
        self.add_node(u)
        self.add_node(v)
        self.adj[u].append(v)

    def n_edges(self) -> int:
        return sum(len(v) for v in self.adj.values())

    def scc(self) -> List[List[str]]:
        """Tarjan's algorithm, iterative."""
        index, low, onstack, stack, out = {}, {}, set(), [], []
        counter = [0]
        for root in list(self.adj):
            if root in index:
                continue
            work = [(root, iter(self.adj[root]))]
            index[root] = low[root] = counter[0]; counter[0] += 1
            stack.append(root); onstack.add(root)
            while work:
                v, it = work[-1]
                advanced = False
                for w in it:
                    if w not in index:
                        index[w] = low[w] = counter[0]; counter[0] += 1
                        stack.append(w); onstack.add(w)
                        work.append((w, iter(self.adj[w])))
                        advanced = True
                        break
                    elif w in onstack:
                        low[v] = min(low[v], index[w])
                if advanced:
                    continue
                work.pop()
                if work:
                    low[work[-1][0]] = min(low[work[-1][0]], low[v])
                if low[v] == index[v]:
                    comp = []
                    while True:
                        w = stack.pop(); onstack.discard(w); comp.append(w)
                        if w == v:
                            break
                    out.append(comp)
        return out

    def is_dag(self) -> bool:
        if any(v in self.adj[v] for v in self.adj):
            return False
        return all(len(c) == 1 for c in self.scc())

    def longest_path_length(self) -> int:
        """Longest path (in edges) in a DAG; raises if cyclic."""
        if not self.is_dag():
            raise ValueError("graph has cycles")
        order, seen = [], set()
        for root in self.adj:
            if root in seen:
                continue
            work = [(root, iter(self.adj[root]))]
            seen.add(root)
            while work:
                v, it = work[-1]
                for w in it:
                    if w not in seen:
                        seen.add(w); work.append((w, iter(self.adj[w])))
                        break
                else:
                    work.pop(); order.append(v)
        dist = {v: 0 for v in self.adj}
        for v in order:  # reverse topological: successors first
            for w in self.adj[v]:
                dist[v] = max(dist[v], dist[w] + 1)
        return max(dist.values()) if dist else 0

    def degree_stats(self) -> dict:
        indeg = Counter(w for vs in self.adj.values() for w in vs)
        outd = [len(self.adj[v]) for v in self.adj]
        n = len(self.adj)
        return {"n_nodes": n, "n_edges": self.n_edges(),
                "sources": sum(1 for v in self.adj if indeg[v] == 0),
                "sinks": sum(1 for d in outd if d == 0),
                "mean_out_degree": (sum(outd) / n) if n else 0.0}


def reachable(table: Sequence[int], x: int) -> List[int]:
    seen, out = set(), []
    while x not in seen:
        seen.add(x); out.append(x); x = table[x]
    return out
