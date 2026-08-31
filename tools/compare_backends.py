"""Run the test labels through both extraction backends and compare.

    PYTHONPATH=. python tools/compare_backends.py

Reads ANTHROPIC_API_KEY from the environment or from a .env file in the project root.
The key is never printed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Minimal .env loader - avoids a python-dotenv dependency for one variable.
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))

from app.extract import LATENCY_BUDGET_SECONDS, extract  # noqa: E402
from app.verify import verify  # noqa: E402

APPLICATIONS = {
    "compliant.png":          {"brand_name": "Old Tom Distillery", "alcohol_content": "45% Alc./Vol.", "net_contents": "750 mL"},
    "warning_title_case.png": {"brand_name": "Old Tom Distillery", "alcohol_content": "45% Alc./Vol.", "net_contents": "750 mL"},
    "warning_missing.png":    {"brand_name": "Old Tom Distillery", "alcohol_content": "45% Alc./Vol.", "net_contents": "750 mL"},
    "abv_mismatch.png":       {"brand_name": "Old Tom Distillery", "alcohol_content": "45% Alc./Vol.", "net_contents": "750 mL"},
    "brand_casing.png":       {"brand_name": "Stone's Throw",      "alcohol_content": "45% Alc./Vol.", "net_contents": "750 mL"},
}

EXPECTED = {
    "compliant.png": "match",
    "warning_title_case.png": "mismatch",
    "warning_missing.png": "missing",
    "abv_mismatch.png": "mismatch",
    "brand_casing.png": "match",
}


def run(backend: str, labels_dir: Path) -> tuple[int, float]:
    print(f"\n=== {backend} ===")
    correct, slowest = 0, 0.0

    for filename, application in APPLICATIONS.items():
        path = labels_dir / filename
        if not path.exists():
            print(f"  {filename}: missing - run tools/make_test_labels.py first")
            continue

        try:
            extraction = extract(path.read_bytes(), filename, backend=backend)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {filename:24} {type(exc).__name__}: {exc}")
            continue

        report = verify(application, extraction.fields.model_dump())
        expected = EXPECTED[filename]
        ok = report.status.value == expected
        correct += ok
        slowest = max(slowest, extraction.elapsed_seconds)

        budget = "" if extraction.elapsed_seconds <= LATENCY_BUDGET_SECONDS else "  OVER BUDGET"
        print(f"  {'OK ' if ok else 'XX '}{filename:24} -> {report.status.value:9} "
              f"(expected {expected:9}) {extraction.elapsed_seconds:5.2f}s "
              f"[{extraction.backend}]{budget}")

        if not ok:
            for result in report.results:
                if result.status.value != "match":
                    print(f"        {result.field_name}: {result.note}")
                    print(f"          read: {str(result.found)[:100]!r}")

    print(f"  {correct}/{len(APPLICATIONS)} correct, slowest {slowest:.2f}s "
          f"(budget {LATENCY_BUDGET_SECONDS:.0f}s)")
    return correct, slowest


def main() -> None:
    labels_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "test_labels")

    run("tesseract", labels_dir)

    if os.environ.get("ANTHROPIC_API_KEY"):
        run("claude", labels_dir)
    else:
        print("\n=== claude ===\n  skipped - no ANTHROPIC_API_KEY in the environment or .env")


if __name__ == "__main__":
    main()
