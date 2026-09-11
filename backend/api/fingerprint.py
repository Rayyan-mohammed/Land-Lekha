"""Tamper-evident fingerprint of a verified land record.

The fingerprint is a SHA-256 over the record's legal content (location, account,
owners, parcels, mutation, registration) in a canonical JSON form. It is printed on the
extract and in its QR code; the public verify endpoint recomputes it from the database, so
any later change to the record (or a forged paper extract) no longer matches.
"""
from __future__ import annotations

import hashlib
import json

from .models import LandRecord

CONTENT_FIELDS = ("owner_name", "father_name", "khata_number", "khasra_number", "survey_number", "plot_area",
                  "land_classification", "village", "tehsil", "district", "state", "mutation_number",
                  "mutation_date", "registration_number", "registration_date", "owners", "parcels")


def record_content(r: LandRecord) -> dict:
    return {"record_id": r.id, **{f: getattr(r, f, None) for f in CONTENT_FIELDS}}


def fingerprint(r: LandRecord) -> str:
    canonical = json.dumps(record_content(r), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def short(fp: str) -> str:
    """Human-readable form printed on paper: 16 hex chars in groups of four."""
    return "-".join(fp[i:i + 4] for i in range(0, 16, 4)).upper()
