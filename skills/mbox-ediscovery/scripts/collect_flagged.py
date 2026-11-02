#!/usr/bin/env python3
"""Copy flagged messages (and their attachments) into a self-contained
flagged_emails/ folder for handoff, given the findings produced by the
classification pass.

findings.json shape: {"findings": [{"message_id": ..., "relevant": true, ...}, ...]}

Message ids match build_batches.py: "idx-<N>", the message's position in the
mbox. Message-Id headers are not unique (exports often hold several copies of
one message), so they are never used as keys.

Run:
  python3 collect_flagged.py --case-dir path/to/case_dir --findings path/to/findings.json --mbox path/to/export.mbox
Writes: <case-dir>/flagged_emails/<date>_idx-<N>/{original.eml, body.txt, attachments/...}
"""
import argparse
import email
import email.policy
import json
import mailbox
from pathlib import Path

from ingest import resolve_mbox


def _modern_message_factory(fp):
    return email.message_from_binary_file(fp, policy=email.policy.default)


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case-dir", required=True, type=Path)
    ap.add_argument("--findings", required=True, type=Path)
    ap.add_argument("--mbox", required=True, type=Path)
    args = ap.parse_args()

    manifest = {f"idx-{m['index']}": m
                for m in load_jsonl(args.case_dir / "manifest.jsonl")}
    findings = json.loads(args.findings.read_text())["findings"]
    relevant_ids = {f["message_id"] for f in findings if f.get("relevant")}
    wanted = {manifest[mid]["index"]: manifest[mid] for mid in relevant_ids if mid in manifest}
    missing = sorted(relevant_ids - manifest.keys())

    out_root = args.case_dir / "flagged_emails"
    out_root.mkdir(parents=True, exist_ok=True)

    written = 0
    box = mailbox.mbox(str(resolve_mbox(args.mbox)), factory=_modern_message_factory)
    for i, raw_msg in enumerate(box):
        m = wanted.get(i)
        if not m:
            continue
        short_id = f"idx-{i}"
        folder = out_root / f"{(m['date'] or 'undated')[:10]}_{short_id}"
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / "original.eml").exists():
            raise SystemExit(f"Refusing to overwrite {folder}; use a fresh flagged_emails/ folder")
        (folder / "original.eml").write_bytes(raw_msg.as_bytes())
        (folder / "body.txt").write_text(m["body_text"] or "")
        for h in m["attachment_hashes"]:
            matches = list((args.case_dir / "attachments").glob(f"{h}*"))
            if matches:
                att_dir = folder / "attachments"
                att_dir.mkdir(exist_ok=True)
                (att_dir / matches[0].name).write_bytes(matches[0].read_bytes())
        written += 1

    print(f"Wrote {written} flagged message folders to {out_root}")
    if missing:
        print(f"WARNING: {len(missing)} flagged id(s) not found in manifest: {missing}")


if __name__ == "__main__":
    main()
