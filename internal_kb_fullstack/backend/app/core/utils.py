from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_whitespace(value: str) -> str:
    value = value.replace("\x00", " ")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()



def _normalized_slug_seed(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().lower()



def slugify(value: str) -> str:
    normalized = _normalized_slug_seed(value)
    normalized = re.sub(r"[^\w\s-]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"[-\s]+", "-", normalized, flags=re.UNICODE).strip("-")
    return normalized or sha256_text(value)[:12]



def heading_anchor(value: str) -> str:
    return slugify(value)



def vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
