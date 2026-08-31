# Label Check — TTB Alcohol Label Verification Prototype

A standalone prototype that compares a label image against the data submitted on its
application, and tells a compliance agent whether they match.

Built for the Treasury IT Specialist (AI) take-home assessment.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional, for the higher-accuracy image reader:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Optional, for the local OCR fallback (only needed if you run without an API key):

```bash
brew install tesseract        # macOS
apt-get install tesseract-ocr # Debian/Ubuntu
```

## Run

```bash
uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>.

### Docker

The app shells out to the `tesseract` binary, so a plain Python buildpack will install
the Python packages and then fail at request time. Use the image:

```bash
docker build -t label-check .
docker run --rm -p 8000:8000 -e ANTHROPIC_API_KEY=sk-ant-... label-check
```

Omit the key and it runs on OCR alone. The build runs `pytesseract.get_tesseract_version()`
as its last step, so a missing or misinstalled OCR binary fails the build rather than
the first request.

## Test

```bash
python -m pytest tests/ -q
```

19 tests cover the comparison rules. They need no API key and no network.

### Test labels

```bash
PYTHONPATH=. python tools/make_test_labels.py test_labels
```

Renders five labels covering the interesting cases: compliant, warning in title case,
warning absent, ABV disagreeing with the application, and a brand differing only by
casing and apostrophe. All five have been run end to end through the OCR backend and
produce the expected verdicts (match / mismatch / missing / mismatch / match).

These are rendered, not photographed — clean, straight, evenly lit. They prove the
pipeline; they say nothing about accuracy on a phone photo of a curved bottle.

---

## What has actually been run

Stated precisely, because "it works" is cheap to claim:

| Check | Result |
|---|---|
| Unit tests over the comparison rules | 19/19 pass |
| Five test labels, end to end, OCR backend | 5/5 correct verdicts, slowest 0.19s |
| `POST /api/verify` with a real image | 200, correct verdict, 0.18s |
| `POST /api/verify-batch`, 4 images + CSV | correct verdicts; unmatched CSV row reported, not dropped |
| Fallback under a live API failure | 5/5 still correct via OCR after a real 401, 0.24-0.57s |
| Claude vision backend, Haiku 4.5 | 15/15 correct across 3 runs, slowest 3.35s, all inside budget |
| Claude vision backend, Opus 5 | 5/5 correct, slowest 6.53s, 3 of 5 over budget |
| Fast mode | **never run** — development account had a fast-mode limit of zero |
| Docker image build | **never run** — no Docker on the development machine |

The fallback row is the one worth reading twice: those five were not simulated failures.
The API genuinely rejected the credential five times, and the application returned the
right answer on every label anyway. That is Marcus's blocked-endpoint scenario, observed
rather than asserted.

Every figure here is on rendered labels, which are the easy case. None of it predicts
accuracy or latency on a photographed bottle under bad lighting.

## Approach

The interview notes describe a job that is mostly **comparison**, not analysis: an agent
reads a number off a form, reads the same number off an image, and decides whether they
agree. So the system splits along that seam:

| Module | Job |
|---|---|
| `app/extract.py` | Turn a label image into text fields. The hard, fuzzy part. |
| `app/verify.py` | Compare those fields to the application. Deterministic, no model. |
| `app/main.py` | HTTP surface, single and batch. |

Keeping comparison out of the model is deliberate. Rules like "the government warning
must be word-for-word" are legal requirements with exact answers; a model asked to judge
them will occasionally be generous. `verify.py` is pure functions over strings, so every
rule is unit-testable and an agent can be told exactly why something was rejected.

### Reading the image

Two backends:

- **Claude (`claude-haiku-4-5`)** — used when `ANTHROPIC_API_KEY` is set. Handles the
  angled, glared, and poorly-lit photographs Jenny described, which is where plain OCR
  falls over. Images are downscaled to 1024px on the long edge first, since image
  tokens dominate request latency.
- **Tesseract** — local OCR, no outbound network. Used when no key is present, and
  automatically as a fallback if the API call fails.

The fallback is not decoration. Marcus said the firewall blocked the previous vendor's
ML endpoints and half their features died. A deployment behind that policy still
returns results here, with reduced accuracy on difficult images, instead of returning
nothing.

#### Why Haiku and not a larger model

Transcription is not a reasoning task, and Sarah's five seconds is a requirement rather
than a preference. Measured on the five test labels, images downscaled, `effort: "low"`
where the model accepts it:

| Model | Correct | Range | Inside 5s |
|---|---|---|---|
| `claude-opus-5` | 5/5 | 4.0–6.5s | 2 of 5 |
| `claude-haiku-4-5` | 5/5 | 1.8–3.5s | 5 of 5 |

Equal accuracy, half the latency. Opus is the better model and loses anyway, because
the constraint that decides adoption here is the clock. `LABEL_MODEL` swaps it back for
anyone whose priorities differ.

The honest limit on that table: the labels are clean and rendered. Glare, skew, and bad
lighting are exactly where a larger model would be expected to separate, and I had no
photographed artwork to test it on. The accuracy column says "tied on the easy cases",
not "tied".

### The comparison rules

Every rule traces to something a stakeholder said:

| Rule | Source |
|---|---|
| Brand name compared after normalizing case, unicode punctuation, and whitespace | Dave's `STONE'S THROW` vs `Stone's Throw` — obviously the same thing |
| Near-miss brands (≥85% similar) flagged for an agent instead of auto-rejected | Dave: "You need judgment" |
| Government warning must match word-for-word, with `GOVERNMENT WARNING:` in caps | Jenny caught one in title case; that is a rejection |
| Proof cross-checked as exactly twice the ABV | TTB requirement; catches internally inconsistent labels |
| Net contents normalized across mL and L | Same volume, different unit, not a mismatch |
| Worst field result becomes the label's result | An agent should never see "pass" over a failed field |

Each label gets one of four outcomes: **match**, **review** (plausible, needs eyes),
**mismatch**, or **missing**.

### The interface

Sarah's benchmark was her 73-year-old mother, and half the team is over 50. So: 20px
base type, two numbered steps, one button, a full-width colored banner stating the
result in plain English, and a table showing each check with the application value and
the label value side by side. No icons standing in for words, no hover-only affordances,
visible focus rings throughout. It is one static HTML file with no external requests —
which also means it renders behind the firewall.

### Batch

`POST /api/verify-batch` takes up to 300 images plus a CSV, matching rows to images by
filename so a 300-file drop does not depend on upload order. Labels are processed
concurrently, capped at 8 in flight. Unmatched images and unmatched CSV rows are both
reported rather than silently dropped.

---

## Latency

Sarah's constraint was explicit: the previous vendor took 30–40 seconds per label and
agents abandoned it. The target is 5 seconds.

Every response carries `elapsed_seconds` and `within_latency_budget`, and the UI says so
when a check ran long — the number is visible rather than buried, because a tool that
quietly drifts past 5 seconds is a tool that gets abandoned again.

**The budget is enforced, not hoped for.** Across 15 measured vision calls the median
was ~2.7s, but the tail crossed 5s twice. So the API request carries a hard 4-second
timeout and no retries, leaving roughly a second for the OCR fallback to finish inside
the budget. A slow read degrades to a worse read; it never becomes a slow response.
That is the specific failure that killed the last vendor pilot, and the one thing this
prototype should be structurally incapable of repeating.

Tunable via `LABEL_VISION_TIMEOUT` if the trade-off should sit elsewhere.

Fast mode (`LABEL_FAST_MODE=1`) runs the same model at up to 2.5× output speed for
premium pricing. It is implemented but was not usable during development — the
development account had a fast-mode rate limit of zero — so it remains untested.

---

## Assumptions and limitations

Stated plainly, since the brief asks for them:

1. **No COLA integration.** Marcus said explicitly this is a standalone proof of
   concept. Applications come in through the form or the batch CSV.
2. **Nothing is persisted.** Images live in memory for the length of the request. No
   database, no uploads directory — the simplest correct answer to "there are PII
   considerations" for a prototype.
3. **No authentication.** Out of scope for a prototype; a real deployment would sit
   behind agency SSO.
4. **The warning text is hardcoded** to the standard statement in 27 CFR 16.21. It is
   the same on every product, so a config lookup would be ceremony without benefit.
5. **Beverage-type-specific rules are not implemented.** Class/type designation, bottler
   address, and country-of-origin requirements vary across beer, wine, and spirits. The
   extractor pulls those fields; the rules for them are the obvious next increment.
6. **Brand near-match threshold (85%) is a starting point,** not a tuned value. It wants
   calibration against real rejected applications.
7. **OCR fallback quality is materially worse** on skewed or glared images. That is the
   documented trade-off for working with no outbound network, not an oversight.
8. **Not tested against real TTB artwork.** Both backends pass all five synthetic
   labels, but rendered text is the easy case. The extraction prompt is written to
   transcribe rather than interpret; accuracy on photographed bottles — angles, glare,
   curved surfaces — is unmeasured, and that is precisely where the model choice above
   would deserve revisiting.

## What I'd do next

- Measure extraction accuracy against a real labeled sample, and tune the near-match
  threshold from rejection data rather than intuition.
- Add the per-beverage-type rules (§5 above).
- Return a confidence signal per field, so "review" can be ranked by how uncertain the
  read was rather than treated as one undifferentiated bucket.
- Batch results export as CSV, so a 300-label run lands back in an agent's normal tools.

## Tools used

FastAPI, Pydantic, the Anthropic Python SDK, Pillow + pytesseract for the offline path,
pytest. No frontend framework — the interface is one HTML file.
