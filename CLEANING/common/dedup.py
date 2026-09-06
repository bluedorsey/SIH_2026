"""
Exact + near-duplicate detection.

Two layers:
1. exact   - identical `dedup_key(text)` (case/punctuation-insensitive)
2. near    - MinHash over word 3-gram shingles with LSH banding, then an
             exact Jaccard check on candidate pairs.  Pure numpy, no
             `datasketch` dependency, fast enough for ~100k short texts.

The same event reported twice must count as ONE incident, otherwise the
dashboard (and the training set) double-count it - see edge case 14 in
the problem notes.
"""
from __future__ import annotations
import re
from collections import defaultdict
from typing import Iterable
import numpy as np
from .text import dedup_key

_MERSENNE = (1 << 61) - 1
_MAX_HASH = (1 << 32) - 1


def _shingles(key: str, n: int = 3) -> set[str]:
    toks = key.split()
    if len(toks) < n:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i:i + n]) for i in range(len(toks) - n + 1)}


def _hash_shingle(s: str) -> int:
    # stable across runs / platforms (Python's hash() is salted per process)
    h = 2166136261
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 16777619) & 0xFFFFFFFF
    return h


class NearDupIndex:
    """MinHash-LSH index. Call `add(id, text)` for every row, then `groups()`."""

    def __init__(self, num_perm: int = 64, threshold: float = 0.85, seed: int = 7):
        rng = np.random.RandomState(seed)
        self.num_perm = num_perm
        self.threshold = threshold
        self.a = rng.randint(1, _MERSENNE, size=num_perm, dtype=np.int64)
        self.b = rng.randint(0, _MERSENNE, size=num_perm, dtype=np.int64)
        # bands/rows chosen so that the LSH curve crosses ~threshold
        self.bands = 16 if num_perm >= 64 else 8
        self.rows = num_perm // self.bands
        self.sigs: dict[str, np.ndarray] = {}
        self.shingles: dict[str, set[str]] = {}
        self.buckets: list[dict[bytes, list[str]]] = [defaultdict(list) for _ in range(self.bands)]

    def _signature(self, sh: set[str]) -> np.ndarray:
        if not sh:
            return np.full(self.num_perm, _MAX_HASH, dtype=np.int64)
        hv = np.array([_hash_shingle(s) for s in sh], dtype=np.int64)
        # (a*x + b) mod p, then mod 2^32 -> min over shingles
        m = (np.outer(self.a, hv) + self.b[:, None]) % _MERSENNE
        return (m & _MAX_HASH).min(axis=1)

    def add(self, rid: str, text: str) -> None:
        sh = _shingles(dedup_key(text))
        sig = self._signature(sh)
        self.sigs[rid] = sig
        self.shingles[rid] = sh
        for bi in range(self.bands):
            band = sig[bi * self.rows:(bi + 1) * self.rows].tobytes()
            self.buckets[bi][band].append(rid)

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

    def pairs(self) -> list[tuple[str, str, float]]:
        seen: set[tuple[str, str]] = set()
        out: list[tuple[str, str, float]] = []
        for bucket in self.buckets:
            for ids in bucket.values():
                if len(ids) < 2:
                    continue
                for i in range(len(ids)):
                    for j in range(i + 1, len(ids)):
                        p = (ids[i], ids[j]) if ids[i] < ids[j] else (ids[j], ids[i])
                        if p in seen:
                            continue
                        seen.add(p)
                        jac = self._jaccard(self.shingles[p[0]], self.shingles[p[1]])
                        if jac >= self.threshold:
                            out.append((p[0], p[1], round(jac, 3)))
        return out

    def groups(self, rank: dict[str, int] | None = None) -> dict[str, str]:
        """Return {row_id: canonical_id} for every row that is a near-duplicate of another row.

        Union-find over the candidate pairs.  The canonical id of a group is the
        member with the highest `rank` (default 0), ties broken by the lexically
        smallest id (= first inserted for our ids).
        """
        rank = rank or {}
        parent: dict[str, str] = {}

        def better(x: str, y: str) -> bool:
            return (rank.get(x, 0), -_ord(x)) > (rank.get(y, 0), -_ord(y))

        def find(x: str) -> str:
            parent.setdefault(x, x)
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for a, b, _ in self.pairs():
            ra, rb = find(a), find(b)
            if ra != rb:
                if better(ra, rb):
                    parent[rb] = ra
                else:
                    parent[ra] = rb
        return {x: find(x) for x in parent if find(x) != x}


_ORD_CACHE: dict[str, int] = {}


def _ord(x: str) -> int:
    """Stable ordering key for ids: smaller = inserted earlier (ids are assigned in insertion order)."""
    if x not in _ORD_CACHE:
        _ORD_CACHE[x] = len(_ORD_CACHE)
    return _ORD_CACHE[x]


def exact_dup_map(rows: Iterable[tuple[str, str]], rank: dict[str, int] | None = None) -> dict[str, str]:
    """rows = (id, text). Returns {dup_id: canonical_id} for exact (normalised) duplicates.

    The canonical row is the highest-`rank` member of the group (first seen on ties).
    """
    rank = rank or {}
    groups: dict[str, list[str]] = {}
    for rid, text in rows:
        _ord(rid)
        k = dedup_key(text)
        if k:
            groups.setdefault(k, []).append(rid)
    dups: dict[str, str] = {}
    for ids in groups.values():
        if len(ids) < 2:
            continue
        canon = max(ids, key=lambda i: (rank.get(i, 0), -_ord(i)))
        for i in ids:
            if i != canon:
                dups[i] = canon
    return dups


_PREFIX_RE = re.compile(r"\s+")


def mark_duplicates(rows: list[dict], text_field: str = "text", id_field: str = "id",
                    threshold: float = 0.85, num_perm: int = 64,
                    priority: "callable | None" = None) -> dict:
    """Annotate rows in place with `is_duplicate`, `duplicate_of`, `dup_kind` (+ `duplicate_ids` on the kept row).

    `priority(row) -> int` decides which member of a duplicate group is kept
    (highest wins; first seen on ties).  Rows are never deleted here - the
    caller decides whether to drop them (training) or keep them (dashboard counts).
    """
    rank = {r[id_field]: int(priority(r)) for r in rows} if priority else {}
    for r in rows:
        _ord(r[id_field])
    exact = exact_dup_map(((r[id_field], r.get(text_field, "")) for r in rows), rank=rank)
    idx = NearDupIndex(num_perm=num_perm, threshold=threshold)
    for r in rows:
        if r[id_field] in exact:
            continue
        idx.add(r[id_field], r.get(text_field, ""))
    near = idx.groups(rank=rank)
    n_exact = n_near = 0
    kept_of: dict[str, list[str]] = {}
    for r in rows:
        rid = r[id_field]
        if rid in exact:
            r["is_duplicate"], r["duplicate_of"], r["dup_kind"] = True, exact[rid], "exact"
            n_exact += 1
        elif rid in near:
            r["is_duplicate"], r["duplicate_of"], r["dup_kind"] = True, near[rid], "near"
            n_near += 1
        else:
            r["is_duplicate"], r["duplicate_of"], r["dup_kind"] = False, None, None
        if r["is_duplicate"]:
            kept_of.setdefault(r["duplicate_of"], []).append(rid)
    for r in rows:
        r["duplicate_ids"] = kept_of.get(r[id_field]) or None
    return {"exact_duplicates": n_exact, "near_duplicates": n_near, "threshold": threshold}
