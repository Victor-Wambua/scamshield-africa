"""Near-duplicate message similarity: word-shingled MinHash (own implementation, no external service)."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable

from .normalize import canonical_text

NUM_PERM = 64
_PRIME = (1 << 61) - 1
_MASK = (1 << 32) - 1


def _coeffs(n: int) -> list[tuple[int, int]]:
    out = []
    for i in range(n):
        d = hashlib.blake2b(f"perm-{i}".encode(), digest_size=16).digest()
        a = int.from_bytes(d[:8], "big") % (_PRIME - 1) + 1
        b = int.from_bytes(d[8:], "big") % _PRIME
        out.append((a, b))
    return out


_COEFFS = _coeffs(NUM_PERM)


def tokens(text: str) -> list[str]:
    t = canonical_text(text)
    cleaned = "".join(ch if ch.isalnum() or ch in "<>" else " " for ch in t)
    return cleaned.split()


def shingles(text: str, k: int = 3) -> set[str]:
    toks = tokens(text)
    if len(toks) < k:
        return {" ".join(toks)} if toks else set()
    return {" ".join(toks[i : i + k]) for i in range(len(toks) - k + 1)}


def _h32(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=4).digest(), "big") & _MASK


def minhash(text: str) -> list[int]:
    sh = shingles(text)
    if not sh:
        return []
    hs = [_h32(s) for s in sh]
    return [min((a * h + b) % _PRIME for h in hs) for a, b in _COEFFS]


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def estimate_similarity(sig_a: list[int], sig_b: list[int]) -> float:
    if not sig_a or not sig_b or len(sig_a) != len(sig_b):
        return 0.0
    return sum(1 for x, y in zip(sig_a, sig_b, strict=True) if x == y) / len(sig_a)


def most_similar(
    sig: list[int], candidates: Iterable[tuple[int, list[int]]], threshold: float = 0.5, limit: int = 5
) -> list[tuple[int, float]]:
    scored = [(cid, estimate_similarity(sig, csig)) for cid, csig in candidates]
    hits = [(cid, s) for cid, s in scored if s >= threshold]
    hits.sort(key=lambda x: (-x[1], x[0]))
    return hits[:limit]
