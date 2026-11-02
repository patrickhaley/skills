#!/usr/bin/env python3
"""Ingest an mbox export (Google Vault, Gmail Takeout, Thunderbird, Apple
Mail, etc.) into the per-case working set used by the rest of the
mbox-ediscovery skill: a
message manifest, deduped attachment store, and per-attachment extracted text.

Tags likely-noise messages (calendar invites, auto-replies, bounces) rather
than dropping them, so nothing disappears from the record silently.
Reconstructs conversation threads via Message-Id/In-Reply-To/References,
falling back to normalized-subject grouping when those headers are absent.

Run:
  python3 ingest.py --mbox path/to/export.mbox --out-dir path/to/case_dir
"""
import argparse
import email
import email.policy
import json
import mailbox
import re
import sys
from email.utils import parsedate_to_datetime
from pathlib import Path

from attachments import extract_pdf_text, is_decorative_image, list_zip_contents, save_unique_attachment


def _modern_message_factory(fp):
    return email.message_from_binary_file(fp, policy=email.policy.default)

NOISE_SUBJECT_PATTERNS = [
    re.compile(r"^automatic reply:", re.I),
    re.compile(r"^out of office", re.I),
    re.compile(r"^undeliverable:", re.I),
    re.compile(r"^delivery status notification", re.I),
]
NOISE_FROM_PATTERNS = [
    re.compile(r"mailer-daemon", re.I),
    re.compile(r"postmaster", re.I),
]


def resolve_mbox(path: Path) -> Path:
    """Accept an mbox file, or an Apple Mail .mbox export folder (which holds
    the actual mailbox in a file named "mbox")."""
    if path.is_dir():
        inner = path / "mbox"
        if not inner.is_file():
            raise SystemExit(f"{path} is a folder with no 'mbox' file inside")
        return inner
    return path


def normalize_subject(subject: str) -> str:
    s = subject or ""
    s = re.sub(r"^\s*(re|fwd?)\s*:\s*", "", s, flags=re.I)
    return s.strip().lower()


def classify_noise(msg, content_types):
    subject = msg.get("Subject", "") or ""
    sender = msg.get("From", "") or ""
    auto_submitted = (msg.get("Auto-Submitted") or "").lower()
    if auto_submitted not in ("", "no"):
        return "auto_reply"
    for pat in NOISE_SUBJECT_PATTERNS:
        if pat.search(subject):
            return "auto_reply_or_bounce"
    for pat in NOISE_FROM_PATTERNS:
        if pat.search(sender):
            return "bounce"
    if "text/calendar" in content_types:
        return "calendar_invite"
    return None


def get_body_text(msg):
    """Prefer text/plain (and text/calendar, so invite bodies are still
    visible for noise review); fall back to a crude strip of text/html."""
    plain, html, content_types = None, None, set()
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            content_types.add(ctype)
            if part.get_content_disposition() == "attachment":
                continue
            if ctype in ("text/plain", "text/calendar") and plain is None:
                plain = part.get_content()
            elif ctype == "text/html" and html is None:
                html = part.get_content()
    else:
        content_types.add(msg.get_content_type())
        plain = msg.get_content()
    if plain:
        return plain, content_types
    if html:
        return re.sub(r"<[^>]+>", " ", html), content_types
    return "", content_types


def build_thread_ids(messages):
    by_id = {m["message_id"]: m for m in messages if m["message_id"]}

    def find_root(mid, seen):
        if mid in seen:
            return mid
        seen.add(mid)
        m = by_id.get(mid)
        if not m or not m["in_reply_to"] or m["in_reply_to"] not in by_id:
            return mid
        return find_root(m["in_reply_to"], seen)

    thread_of = {}
    for m in messages:
        mid = m["message_id"]
        if mid and mid in by_id:
            thread_of[mid] = find_root(mid, set())

    subject_groups = {}
    for m in messages:
        mid = m["message_id"]
        if mid in thread_of:
            m["thread_id"] = thread_of[mid]
            continue
        key = normalize_subject(m["subject"])
        subject_groups.setdefault(key, mid or key)
        m["thread_id"] = subject_groups[key]
    return messages


def process_attachments(msg, store_dir: Path, seen_hashes: dict):
    hashes = []
    if not msg.is_multipart():
        return hashes
    for part in msg.walk():
        filename = part.get_filename()
        if part.get_content_disposition() != "attachment" and not filename:
            continue
        data = part.get_payload(decode=True)
        if not data:
            continue
        digest, path = save_unique_attachment(data, filename or "unnamed", store_dir)
        hashes.append(digest)
        if digest in seen_hashes:
            continue
        ctype = part.get_content_type()
        decorative = False
        if ctype == "application/pdf" or path.suffix.lower() == ".pdf":
            text, kind, needs_ocr = extract_pdf_text(path), "pdf", False
        elif path.suffix.lower() == ".zip" or ctype == "application/zip":
            text, kind, needs_ocr = "\n".join(list_zip_contents(path)), "zip", False
        elif ctype.startswith("image/"):
            decorative = is_decorative_image(filename or "", len(data))
            text, kind, needs_ocr = "", "image", not decorative
        else:
            text, kind, needs_ocr = "", "other", False
        seen_hashes[digest] = {
            "hash": digest, "filename": filename or "unnamed", "kind": kind,
            "text": text, "needs_ocr": needs_ocr, "decorative": decorative,
            "path": str(path),
        }
    return hashes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mbox", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    attachments_dir = args.out_dir / "attachments"
    seen_hashes = {}

    box = mailbox.mbox(str(resolve_mbox(args.mbox)), factory=_modern_message_factory)
    messages = []
    for i, msg in enumerate(box):
        body_text, content_types = get_body_text(msg)
        noise_reason = classify_noise(msg, content_types)
        attachment_hashes = process_attachments(msg, attachments_dir, seen_hashes)
        date_hdr = msg.get("Date")
        try:
            date_iso = parsedate_to_datetime(date_hdr).isoformat() if date_hdr else None
        except (TypeError, ValueError):
            date_iso = None
        messages.append({
            "message_id": msg.get("Message-Id"),
            "in_reply_to": msg.get("In-Reply-To"),
            "references": msg.get("References"),
            "index": i,
            "date": date_iso,
            "date_raw": date_hdr,
            "from": msg.get("From"),
            "to": msg.get("To"),
            "cc": msg.get("Cc"),
            "subject": msg.get("Subject", "") or "",
            "body_text": body_text,
            "attachment_hashes": attachment_hashes,
            "is_noise": noise_reason is not None,
            "noise_reason": noise_reason,
        })

    messages = build_thread_ids(messages)

    with (args.out_dir / "manifest.jsonl").open("w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")

    with (args.out_dir / "attachment_text.jsonl").open("w") as f:
        for row in seen_hashes.values():
            f.write(json.dumps(row) + "\n")

    noise_count = sum(1 for m in messages if m["is_noise"])
    print(f"Ingested {len(messages)} messages ({noise_count} tagged noise), "
          f"{len(seen_hashes)} unique attachments.", file=sys.stderr)


if __name__ == "__main__":
    main()
