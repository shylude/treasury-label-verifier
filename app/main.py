"""HTTP surface for the label verification prototype.

Standalone by design - nothing here talks to COLA, and no uploaded image is written
to disk. Images are held in memory for the length of the request and dropped.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .extract import LATENCY_BUDGET_SECONDS, extract
from .verify import verify

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"

# Peak season means importers dropping 200-300 applications at once. Cap concurrency
# so a large batch doesn't exhaust the API rate limit or the box's memory.
BATCH_CONCURRENCY = 8
MAX_BATCH_SIZE = 300
MAX_IMAGE_BYTES = 10 * 1024 * 1024

app = FastAPI(title="TTB Label Verification Prototype", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _require_image(upload: UploadFile, data: bytes) -> None:
    if not data:
        raise HTTPException(400, f"{upload.filename or 'file'} is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(413, f"{upload.filename} exceeds the 10 MB limit.")


def _review_one(image_bytes: bytes, filename: str, application: dict) -> dict:
    extraction = extract(image_bytes, filename)
    report = verify(application, extraction.fields.model_dump())
    return {
        "filename": filename,
        "application": application,
        "status": report.status.value,
        "passed": report.passed,
        "fields": [
            {
                "field": r.field_name,
                "status": r.status.value,
                "expected": r.expected,
                "found": r.found,
                "note": r.note,
            }
            for r in report.results
        ],
        "legible": extraction.fields.legible,
        "backend": extraction.backend,
        "elapsed_seconds": round(extraction.elapsed_seconds, 2),
        "within_latency_budget": extraction.within_budget,
    }


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok", "latency_budget_seconds": LATENCY_BUDGET_SECONDS}


@app.post("/api/verify")
async def verify_one(
    label: UploadFile = File(..., description="Label artwork"),
    brand_name: str = Form(...),
    alcohol_content: str = Form(...),
    net_contents: str = Form(""),
) -> JSONResponse:
    """Check one label against one application record."""
    data = await label.read()
    _require_image(label, data)

    application = {
        "brand_name": brand_name,
        "alcohol_content": alcohol_content,
        "net_contents": net_contents,
    }
    result = await asyncio.to_thread(_review_one, data, label.filename or "label", application)
    return JSONResponse(result)


@app.post("/api/verify-batch")
async def verify_batch(
    labels: list[UploadFile] = File(..., description="One image per application"),
    applications: UploadFile = File(..., description="CSV: filename,brand_name,alcohol_content,net_contents"),
) -> JSONResponse:
    """Check many labels at once.

    Applications are matched to images by the CSV's ``filename`` column so a 300-row
    drop doesn't depend on upload ordering.
    """
    if len(labels) > MAX_BATCH_SIZE:
        raise HTTPException(413, f"Batch limit is {MAX_BATCH_SIZE} labels; received {len(labels)}.")

    raw_csv = (await applications.read()).decode("utf-8-sig")
    rows = {row["filename"]: row for row in csv.DictReader(io.StringIO(raw_csv)) if row.get("filename")}
    if not rows:
        raise HTTPException(400, "Application CSV has no usable rows (needs a 'filename' column).")

    images: list[tuple[str, bytes]] = []
    for upload in labels:
        data = await upload.read()
        _require_image(upload, data)
        images.append((upload.filename or "", data))

    semaphore = asyncio.Semaphore(BATCH_CONCURRENCY)

    async def review(filename: str, data: bytes) -> dict:
        row = rows.get(filename)
        if row is None:
            return {"filename": filename, "status": "unmatched", "passed": False,
                    "fields": [], "note": "No row in the application CSV matches this filename."}
        async with semaphore:
            return await asyncio.to_thread(_review_one, data, filename, row)

    results = await asyncio.gather(*(review(name, data) for name, data in images))

    unmatched_rows = sorted(set(rows) - {name for name, _ in images})
    summary = {
        "total": len(results),
        "passed": sum(1 for r in results if r.get("passed")),
        "needs_review": sum(1 for r in results if r.get("status") == "review"),
        "rejected": sum(1 for r in results if r.get("status") in {"mismatch", "missing"}),
        "unmatched_csv_rows": unmatched_rows,
    }
    return JSONResponse({"summary": summary, "results": results})
