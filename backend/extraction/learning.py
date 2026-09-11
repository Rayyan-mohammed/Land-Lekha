"""Learning from verifier corrections.

Every time a verifier corrects a field, the pair (what OCR read -> what it should be)
is stored. Next time the same misreading appears for that field, the learned value is
applied automatically (and flagged as such). Per-field correction rates also raise the
auto-accept threshold for fields the system keeps getting wrong.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from .confidence import default_threshold
from .normalize import label_key

MIN_REVIEWS_FOR_ADAPT = 5


@dataclass
class CorrectionMemory:
    # (field, normalised raw) -> {corrected value: count}
    subs: dict[tuple[str, str], dict[str, int]] = field(default_factory=lambda: defaultdict(dict))
    # field -> [reviewed, corrected]
    stats: dict[str, list[int]] = field(default_factory=lambda: defaultdict(lambda: [0, 0]))

    def add_correction(self, field_name: str, raw: str | None, corrected: str) -> None:
        if raw:
            bucket = self.subs[(field_name, label_key(raw))]
            bucket[corrected] = bucket.get(corrected, 0) + 1

    def add_review(self, field_name: str, corrected: bool) -> None:
        s = self.stats[field_name]
        s[0] += 1
        s[1] += int(corrected)

    def lookup(self, field_name: str, raw: str) -> str | None:
        bucket = self.subs.get((field_name, label_key(raw)))
        if not bucket:
            return None
        return max(bucket.items(), key=lambda kv: kv[1])[0]

    def field_thresholds(self, base: float | None = None) -> dict[str, float]:
        """Fields corrected often need more confidence before we trust them blindly."""
        base = default_threshold() if base is None else base
        out = {}
        for name, (reviewed, corrected) in self.stats.items():
            if reviewed >= MIN_REVIEWS_FOR_ADAPT:
                rate = corrected / reviewed
                out[name] = round(min(0.95, base + 0.3 * rate), 3)
        return out
