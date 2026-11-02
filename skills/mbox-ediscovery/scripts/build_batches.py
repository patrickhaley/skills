#!/usr/bin/env python3
"""Chunk non-noise messages from a manifest into chronological batches with
full text content (body + any extracted attachment/OCR text), ready to hand
to the Workflow classification pass.

Each batch is written to its own JSONL file under <case-dir>/batches/ (one
JSON object per line) rather than embedded in a single combined file. This
matters at real mailbox scale: a few thousand messages' full body text
easily runs to tens of megabytes, which cannot be inlined into a Workflow
tool call's `args` (that value is constructed directly in the orchestrator's
own context). Writing one file per batch lets each classification sub-agent
`Read` its own batch directly from disk — the orchestrator only ever handles
the small index (batch id, path, message count) written to batch_index.json.

Body/attachment text is truncated per message (see --truncate-chars) since
message length is heavy-tailed — a handful of long quoted-thread messages
can dominate token cost for little marginal signal.

Default --batch-size of 100 is a deliberate tradeoff, not a round number.
Measured on a real ~4,000-message mailbox, per-agent fixed overhead (system
prompt, tool/schema definitions — paid fresh by every classification
sub-agent, since they don't share cache with each other) dominated total
classification cost by roughly 19:1 over actual message content, so fewer
larger batches (fewer sub-agents) meaningfully cuts total tokens. The
ceiling on how far to push this is Haiku's OUTPUT token budget, not its
~200K input context window — content at batch-size 100 tops out around
85K input tokens even in the worst case, comfortably under the window, but
a batch's findings array (one entry per message) can still hit the output
ceiling on a big batch and come back truncated. workflow_classify.js's
prompt instructs sub-agents to keep non-relevant entries minimal (skip
optional fields entirely) specifically to make room for larger batches
without tripping that ceiling, and the retry phase catches any batch that
still comes back short. Push batch-size higher than 100 only after
confirming batchesStillShortAfterRetry stays low at that size.

Scope filters from the pre-flight questions are applied here:
--start-date / --end-date (inclusive, YYYY-MM-DD) and --exclude-address
(repeatable; drops a message when its From matches, case-insensitive
substring). Undated messages are kept so nothing drops out silently.

Run:
  python3 build_batches.py --case-dir path/to/case_dir --batch-size 100 \
      [--start-date 2024-01-01] [--end-date 2024-12-31] [--exclude-address noreply@example.com]
Writes: <case-dir>/batches/batch_NNNN.jsonl, <case-dir>/batch_index.json
"""
import argparse
import json
from pathlib import Path


def load_jsonl(path: Path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def truncate(text: str, cap: int) -> str:
    if not text:
        return ""
    if len(text) <= cap:
        return text
    return text[:cap] + "...[truncated]"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case-dir", required=True, type=Path)
    ap.add_argument("--batch-size", type=int, default=100)
    ap.add_argument("--truncate-chars", type=int, default=4000,
                     help="Per-message cap applied separately to body_text and attachment_text.")
    ap.add_argument("--start-date", help="Inclusive, YYYY-MM-DD.")
    ap.add_argument("--end-date", help="Inclusive, YYYY-MM-DD.")
    ap.add_argument("--exclude-address", action="append", default=[],
                     help="Drop messages whose From contains this (repeatable).")
    args = ap.parse_args()

    manifest = load_jsonl(args.case_dir / "manifest.jsonl")
    attachment_text = {row["hash"]: row for row in load_jsonl(args.case_dir / "attachment_text.jsonl")}

    excluded = [a.lower() for a in args.exclude_address]

    def in_scope(m):
        day = (m["date"] or "")[:10]
        if day and args.start_date and day < args.start_date:
            return False
        if day and args.end_date and day > args.end_date:
            return False
        sender = (m["from"] or "").lower()
        return not any(a in sender for a in excluded)

    non_noise = [m for m in manifest if not m["is_noise"]]
    active = [m for m in non_noise if in_scope(m)]
    active.sort(key=lambda m: m["date"] or "")

    batches_dir = args.case_dir / "batches"
    batches_dir.mkdir(exist_ok=True)

    batch_index = []
    for start in range(0, len(active), args.batch_size):
        chunk = active[start:start + args.batch_size]
        batch_id = len(batch_index)
        out_path = batches_dir / f"batch_{batch_id:04d}.jsonl"
        with out_path.open("w") as f:
            for m in chunk:
                att_texts = [attachment_text[h]["text"] for h in m["attachment_hashes"]
                             if h in attachment_text and attachment_text[h]["text"]]
                row = {
                    "id": f"idx-{m['index']}",  # unique; Message-Ids repeat across copies of a message
                    "date": m["date"],
                    "from": m["from"],
                    "to": m["to"],
                    "subject": m["subject"],
                    "body_text": truncate(m["body_text"] or "", args.truncate_chars),
                    "attachment_text": truncate("\n---\n".join(att_texts), args.truncate_chars),
                }
                f.write(json.dumps(row) + "\n")
        batch_index.append({"batch_id": batch_id, "path": str(out_path.resolve()), "count": len(chunk)})

    (args.case_dir / "batch_index.json").write_text(json.dumps(batch_index, indent=2))
    print(f"Wrote {len(batch_index)} batch files ({batches_dir}/) covering {len(active)} messages "
          f"({len(manifest)} total, {len(manifest) - len(non_noise)} noise, "
          f"{len(non_noise) - len(active)} out of scope). Index: {args.case_dir / 'batch_index.json'}")


if __name__ == "__main__":
    main()
