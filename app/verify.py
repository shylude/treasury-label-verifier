"""Field-by-field comparison of an application record against text read off a label.

This module is deliberately free of I/O and model calls: every rule below came out of
the stakeholder interviews, and keeping them here makes them testable in isolation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from enum import Enum

# 27 CFR 16.21. Must appear word-for-word; Jenny flagged that applicants routinely
# reword it, shrink it, or drop it into title case.
GOVERNMENT_WARNING = (
    "GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
    "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
    "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
    "operate machinery, and may cause health problems."
)

WARNING_PREFIX = "GOVERNMENT WARNING:"

# Dave's "STONE'S THROW" vs "Stone's Throw" case: same brand, different casing and
# curly apostrophe. Below this ratio we stop calling it a near-miss and call it wrong.
BRAND_NEAR_MATCH_RATIO = 0.85


class Status(str, Enum):
    MATCH = "match"
    REVIEW = "review"  # plausibly fine, but an agent should lay eyes on it
    MISMATCH = "mismatch"
    MISSING = "missing"


@dataclass
class FieldResult:
    field_name: str
    status: Status
    expected: str | None
    found: str | None
    note: str = ""


@dataclass
class LabelReport:
    results: list[FieldResult] = field(default_factory=list)

    @property
    def status(self) -> Status:
        if any(r.status is Status.MISMATCH for r in self.results):
            return Status.MISMATCH
        if any(r.status is Status.MISSING for r in self.results):
            return Status.MISSING
        if any(r.status is Status.REVIEW for r in self.results):
            return Status.REVIEW
        return Status.MATCH

    @property
    def passed(self) -> bool:
        return self.status is Status.MATCH


def _normalize(text: str) -> str:
    """Casefold, flatten unicode punctuation, collapse whitespace.

    Curly apostrophes and non-breaking spaces show up constantly in artwork exported
    from design tools, and they are never a real compliance difference.
    """
    text = unicodedata.normalize("NFKD", text)
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    text = text.replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip().casefold()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def check_brand_name(expected: str, found: str | None) -> FieldResult:
    if not found:
        return FieldResult("brand_name", Status.MISSING, expected, found,
                           "No brand name could be read from the label.")

    norm_expected, norm_found = _normalize(expected), _normalize(found)
    if norm_expected == norm_found:
        note = ""
        if expected.strip() != found.strip():
            note = "Matches apart from capitalization or punctuation."
        return FieldResult("brand_name", Status.MATCH, expected, found, note)

    ratio = _similarity(norm_expected, norm_found)
    if ratio >= BRAND_NEAR_MATCH_RATIO:
        return FieldResult("brand_name", Status.REVIEW, expected, found,
                           f"Close but not identical ({ratio:.0%} similar) - agent should confirm.")

    return FieldResult("brand_name", Status.MISMATCH, expected, found,
                       "Brand name on the label does not match the application.")


_ABV_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*%")
_PROOF_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*proof", re.IGNORECASE)


def _parse_abv(text: str) -> float | None:
    match = _ABV_PATTERN.search(text)
    if match:
        return float(match.group(1))
    # Some spirits labels lead with proof; TTB treats proof as exactly twice the ABV.
    match = _PROOF_PATTERN.search(text)
    if match:
        return float(match.group(1)) / 2
    return None


def check_alcohol_content(expected: str, found: str | None) -> FieldResult:
    if not found:
        return FieldResult("alcohol_content", Status.MISSING, expected, found,
                           "No alcohol content could be read from the label.")

    expected_abv, found_abv = _parse_abv(expected), _parse_abv(found)
    if expected_abv is None or found_abv is None:
        return FieldResult("alcohol_content", Status.REVIEW, expected, found,
                           "Could not parse a percentage from one of the values.")

    if abs(expected_abv - found_abv) < 0.05:
        note = ""
        proof = _PROOF_PATTERN.search(found)
        if proof and abs(float(proof.group(1)) - found_abv * 2) >= 0.1:
            return FieldResult("alcohol_content", Status.MISMATCH, expected, found,
                               f"ABV matches but stated proof ({proof.group(1)}) is not twice the ABV.")
        return FieldResult("alcohol_content", Status.MATCH, expected, found, note)

    return FieldResult("alcohol_content", Status.MISMATCH, expected, found,
                       f"Application says {expected_abv}%, label says {found_abv}%.")


_VOLUME_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(ml|milliliters?|l|liters?|litres?)\b", re.IGNORECASE)


def _parse_volume_ml(text: str) -> float | None:
    match = _VOLUME_PATTERN.search(text)
    if not match:
        return None
    amount, unit = float(match.group(1)), match.group(2).lower()
    return amount * 1000 if unit.startswith("l") and not unit.startswith("ml") else amount


def check_net_contents(expected: str, found: str | None) -> FieldResult:
    if not found:
        return FieldResult("net_contents", Status.MISSING, expected, found,
                           "No net contents could be read from the label.")

    expected_ml, found_ml = _parse_volume_ml(expected), _parse_volume_ml(found)
    if expected_ml is None or found_ml is None:
        return FieldResult("net_contents", Status.REVIEW, expected, found,
                           "Could not parse a volume from one of the values.")

    if abs(expected_ml - found_ml) < 0.5:
        return FieldResult("net_contents", Status.MATCH, expected, found)

    return FieldResult("net_contents", Status.MISMATCH, expected, found,
                       f"Application says {expected_ml:g} mL, label says {found_ml:g} mL.")


def check_government_warning(found: str | None) -> FieldResult:
    """The one check with no tolerance at all - it is exact or it is a rejection."""
    if not found or not found.strip():
        return FieldResult("government_warning", Status.MISSING, GOVERNMENT_WARNING, found,
                           "Mandatory health warning statement is absent.")

    collapsed = re.sub(r"\s+", " ", found).strip()

    # Casing of the prefix is itself a requirement, so this is checked before any
    # normalization that would paper over it.
    prefix_seen = collapsed[: len(WARNING_PREFIX)]
    if prefix_seen.upper() != WARNING_PREFIX:
        return FieldResult("government_warning", Status.MISMATCH, GOVERNMENT_WARNING, found,
                           "Statement does not begin with 'GOVERNMENT WARNING:'.")
    if prefix_seen != WARNING_PREFIX:
        return FieldResult("government_warning", Status.MISMATCH, GOVERNMENT_WARNING, found,
                           f"'{prefix_seen}' must appear in all capitals.")

    if _normalize(collapsed) == _normalize(GOVERNMENT_WARNING):
        return FieldResult("government_warning", Status.MATCH, GOVERNMENT_WARNING, found)

    ratio = _similarity(_normalize(collapsed), _normalize(GOVERNMENT_WARNING))
    return FieldResult("government_warning", Status.MISMATCH, GOVERNMENT_WARNING, found,
                       f"Wording differs from the required statement ({ratio:.0%} similar); it must be word-for-word.")


def verify(application: dict, extracted: dict) -> LabelReport:
    """Compare one application record against one label's extracted text."""
    report = LabelReport()
    report.results.append(check_brand_name(application.get("brand_name", ""),
                                           extracted.get("brand_name")))
    report.results.append(check_alcohol_content(application.get("alcohol_content", ""),
                                                extracted.get("alcohol_content")))
    if application.get("net_contents"):
        report.results.append(check_net_contents(application["net_contents"],
                                                 extracted.get("net_contents")))
    report.results.append(check_government_warning(extracted.get("government_warning")))
    return report
