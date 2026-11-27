"""Message catalogues. English is the source; Swahili strings are drafts needing native review."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

LOCALES = Path(__file__).parent / "locales"
SUPPORTED = ("en", "sw")


@lru_cache(maxsize=8)
def catalog(lang: str) -> dict[str, str]:
    p = LOCALES / f"{lang}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def translate(lang: str, key: str) -> str:
    return catalog(lang).get(key) or catalog("en").get(key) or key


def pick_language(cookie: str | None, user_lang: str | None) -> str:
    for cand in (user_lang, cookie):
        if cand in SUPPORTED:
            return str(cand)
    return "en"
