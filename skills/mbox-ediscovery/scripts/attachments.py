#!/usr/bin/env python3
"""Attachment hashing/dedup and text extraction helpers for the
eDiscovery ingest pipeline.

Dedupes attachments by SHA-256 so identical files attached across many
messages (the same PDF, the same signature image) are only saved and
text-extracted once.
"""
import hashlib
import re
import subprocess
import zipfile
from pathlib import Path

DECORATIVE_FILENAME_PATTERNS = re.compile(
    r"opensense|outlook-image|outlook-\w{6,10}\.(png|jpg)$|social-icon|"
    r"email-icon|cell-icon|address-icon|direct-icon|^image00[0-9]\.(png|gif)$",
    re.I,
)
DECORATIVE_SIZE_THRESHOLD = 15_000  # bytes; small inline logos/social icons


def is_decorative_image(filename: str, size_bytes: int) -> bool:
    """Heuristic for email-signature icons/logos (social icons, Outlook inline
    images, tiny logo graphics) that are never worth OCR'ing. Filename-pattern
    match OR small file size; either alone catches cases the other misses
    (e.g. a small filename-less icon, or a renamed-but-still-tiny logo)."""
    return bool(DECORATIVE_FILENAME_PATTERNS.search(filename or "")) or size_bytes < DECORATIVE_SIZE_THRESHOLD


def hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from a PDF using pdftotext (poppler). Returns '' on failure."""
    try:
        result = subprocess.run(
            ["pdftotext", str(pdf_path), "-"],
            capture_output=True, timeout=120,
        )
        if result.returncode != 0:
            return ""
        return result.stdout.decode("utf-8", errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def list_zip_contents(zip_path: Path) -> list:
    """Return the list of filenames inside a zip, or [] if unreadable."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return zf.namelist()
    except (zipfile.BadZipFile, FileNotFoundError):
        return []


def save_unique_attachment(data: bytes, filename: str, store_dir: Path):
    """Save attachment bytes to store_dir/<sha256><ext> if not already present.

    Returns (hash, path). Callers should treat a pre-existing path as a
    cache hit and skip re-running expensive text extraction for that hash.
    """
    store_dir.mkdir(parents=True, exist_ok=True)
    digest = hash_bytes(data)
    ext = Path(filename).suffix
    out_path = store_dir / f"{digest}{ext}"
    if not out_path.exists():
        out_path.write_bytes(data)
    return digest, out_path
