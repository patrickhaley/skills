#!/usr/bin/env python3
"""Record OCR text for one unique image attachment, identified by its
sha256 hash, back into attachment_text.jsonl.

The orchestrating Claude session runs this after directly reading (via the
Read tool, which supports images natively) each image flagged
needs_ocr: true in attachment_text.jsonl, passing what it read as --text.

Run:
  python3 record_ocr.py --case-dir path/to/case_dir --hash <sha256> --text "extracted text or description here"
"""
import argparse
import json
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", required=True, type=Path)
    ap.add_argument("--hash", required=True)
    ap.add_argument("--text", required=True)
    args = ap.parse_args()

    path = args.case_dir / "attachment_text.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    found = False
    for row in rows:
        if row["hash"] == args.hash:
            row["text"] = args.text
            row["needs_ocr"] = False
            found = True
    if not found:
        raise SystemExit(f"No attachment_text row found for hash {args.hash}")

    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"Recorded OCR text for {args.hash}")


if __name__ == "__main__":
    main()
