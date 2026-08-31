# The app shells out to the tesseract binary for the offline fallback, so a plain
# Python buildpack is not enough - the OS package has to be present in the image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# tesseract-ocr-eng is the language data. Without it the binary installs but reads
# nothing, which fails at request time rather than build time - so it is explicit.
RUN apt-get update \
    && apt-get install --no-install-recommends -y tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Requirements first so the dependency layer survives source-only changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

# Fail the build, not the first request, if the OCR backend is not actually wired up.
RUN python -c "import pytesseract; print(pytesseract.get_tesseract_version())"

# Run unprivileged. Nothing is written to disk at runtime, so no writable volumes.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Hosts inject PORT; default to 8000 for a plain `docker run`.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
