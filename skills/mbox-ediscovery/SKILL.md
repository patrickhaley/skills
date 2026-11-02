---
name: mbox-ediscovery
description: Review an mbox email export (Google Vault, Gmail Takeout, Thunderbird, Apple Mail and others) for a legal or eDiscovery question ("did X ever mention, request or agree to Y?") and produce a facts-only cited report, a ready-to-share pack (report in Word, flagged emails as one bookmarked PDF, CSV index) and a draft handoff email. Use only when the user asks for /mbox-ediscovery.
disable-model-invocation: true
---

# mbox eDiscovery review

Turn an mbox email export into a cited, dated report that can go to a teammate or outside counsel, without grepping raw mail by hand and without missing evidence in duplicate attachments, encoded bodies or images.

The skill presents facts. It never gives legal advice or draws legal conclusions; the requester and their advisers do that.

This is a triage tool. It does not replace a certified eDiscovery platform for a litigation production, and it does no legal hold or chain-of-custody work.

## Ground rules

- Treat the source mbox as read-only. Everything the skill writes goes in the case folder.
- Put the case folder outside any git repo. It holds real mail.
- Tag noise; never delete it. Every excluded, unclassified or unreadable message is counted in the report.
- Every finding cites a date, the participants and a direct quote.
- Facts only, everywhere: in the report, the email and the chat. Say what the emails say and when. Do not say what they mean legally, whether anyone is in the right, or what to do next. If the user asks for that, say it is a question for their legal adviser and offer the relevant quotes instead. `reference/report-template.md` has the detailed rules.

## How the work is split

- **Main session:** ingest, scoping questions, keyword approval, image OCR, collecting flagged emails and writing the report. Anything that needs judgement or the user stays here.
- **Sub-agents (small, cheap model such as Haiku):** only the bulk classification in step 6. Each reads one batch file and returns structured findings. It is the only step that grows with mailbox size.

If findings look wrong, check the batch prompt and keyword list first. Sub-agents only see what the batch prompt gives them.

## Inputs

- One mbox file from any source: Google Vault, Gmail Takeout, Thunderbird and so on. Google Vault's metadata CSV is not needed.
- Apple Mail exports a `.mbox` folder rather than a file. Pass the folder; the scripts use the `mbox` file inside it.
- PST (Outlook) is not supported. Ask the user to export as mbox or convert it first.

Paths below are relative to this skill's folder. Use `<case-dir>` for the case folder; by default this is `<mbox folder>/<mbox name>-ediscovery/`.

## Setup

- Python 3 standard library only. Nothing to install for parsing.
- PDF text needs `pdftotext` (poppler). Check with `which pdftotext`. If it is missing, ask before installing it (`brew install poppler` on macOS). Without it, PDFs are recorded as not machine-readable.
- The share pack (step 9) needs [`uv`](https://docs.astral.sh/uv/) (it fetches `pypdf` for that script only), Google Chrome or Chromium (renders emails to PDF) and macOS `textutil` (writes the Word report). Check before step 9 and ask before installing anything.

## Steps

### 1. Ingest

```bash
python3 scripts/ingest.py --mbox <path.mbox> --out-dir <case-dir>
```

Writes `manifest.jsonl` (one row per message), `attachment_text.jsonl` (one row per unique attachment) and `attachments/` (deduplicated by SHA-256). Calendar invites, auto-replies and bounces are tagged as noise. The subject rules for auto-replies and bounces follow Outlook and Exchange wording; other mail clients' versions are not tagged and simply go through classification. See `reference/manifest-schema.md` and `reference/noise-patterns.md`.

Tell the user the message count, the noise count and the date range before moving on.

### 2. Scoping questions

Follow `reference/preflight-questions.md`: case name, date range, senders to exclude, seed keywords and analysis templates. Then expand the keywords and get the list approved. Nothing is classified until the user approves the list.

### 3. OCR images

Rows in `attachment_text.jsonl` with `needs_ocr: true` are images that need reading. Signature icons and small logos are already tagged `decorative` and skipped.

Only OCR images attached to non-noise messages inside the approved scope. If that is more than about 50, tell the user the count and ask whether to do all of them or only images on messages that mention an approved keyword.

For each image, open it with your file-reading tool (it reads images). Write what it shows to `<case-dir>/ocr/<sha256>.txt` with your file-writing tool, then record it:

```bash
python3 scripts/record_ocr.py --case-dir <case-dir> --hash <sha256> --text-file <case-dir>/ocr/<sha256>.txt
```

Never put image text in the command itself. Images can contain shell syntax such as `$(...)`.

Note anything you skipped for the report.

### 4. Build batches

```bash
python3 scripts/build_batches.py --case-dir <case-dir> --batch-size 100 \
  [--start-date YYYY-MM-DD] [--end-date YYYY-MM-DD] [--exclude-address <addr>]...
```

Applies the approved scope and writes one file per batch to `batches/`, plus a small `batch_index.json` of `{batch_id, path, count}`. Sub-agents read their batch from disk because a real mailbox is too large to pass inline. Body and attachment text are each cut to 4,000 characters per message (`--truncate-chars` to change).

Keep the batch size at 100 unless you have a reason. Fewer, larger batches cost less overall, but a batch that is too large can cut off a sub-agent's output. The script's docstring has the reasoning. Go lower if messages are unusually long.

### 5. Confirm before classifying

Tell the user how many batches and messages will be classified, and get a yes. This step starts many sub-agents.

### 6. Classify

In Claude Code, run the bundled workflow, passing the contents of `batch_index.json` (paths and counts only, not message text):

```
Workflow({
  scriptPath: "<this skill's folder>/scripts/workflow_classify.js",
  args: {
    batchIndex: <contents of batch_index.json>,
    keywords: <approved keyword list>,
    templates: <selected analysis templates>
  }
})
```

Each sub-agent reads one batch and returns a finding for every message. Any batch that returns fewer findings than its message count is retried once.

Without a workflow tool, start one sub-agent per batch using the prompt in `buildPrompt()` in `workflow_classify.js`, and retry short batches the same way.

Save the findings as `{"findings": [...]}` to `<case-dir>/findings.json`. Any batch in `batchesStillShortAfterRetry` goes in the report as unclassified, listed by message id (`idx-<N>`, the message's position in the mbox; its Message-Id is in `manifest.jsonl`).

### 7. Collect flagged emails

```bash
python3 scripts/collect_flagged.py --case-dir <case-dir> --findings <case-dir>/findings.json --mbox <path.mbox>
```

Writes `flagged_emails/<date>_idx-<N>/` with the original `.eml`, the decoded `body.txt` and the attachments for each flagged message. This is the internal working copy; step 9 builds what gets shared.

### 8. Write the report

Follow `reference/report-template.md`. Save it as `<case-dir>/<case-slug>-ediscovery-report-<YYYY-MM-DD>.md`, using today's date, and post it in chat.

Before posting, remove duplicate flags (the same quote can show up on several messages in a thread) and spot-check a few findings against `flagged_emails/`. Then reread the report against the facts-only rules in the template and rewrite any sentence that draws a conclusion.

### 9. Build the share pack

The people receiving the review (often lawyers) need files they can open without special tools. Everything else in the case folder (`.jsonl`, `.json`, `.mbox`, batches) is working data and is never shared.

```bash
uv run scripts/build_share_pack.py --case-dir <case-dir> --findings <case-dir>/findings.json \
  --report <case-dir>/<report>.md --case-name "<case name>"
```

Writes `<case-dir>/share/`:

- `<Case>_Report.docx`: the report in Word. Each `idx-<N>` in the report becomes `Email 0001 (bundle p. 5)`.
- `<Case>_Email_Bundle.pdf`: every flagged email in date order, numbered 0001 onwards. Each email has a header block (date, from, to, cc, subject, attachments), then the body, then its images and PDF attachments. There is a bookmark for every email and PDF attachment. Remote images and scripts in emails are blocked, never loaded.
- `<Case>_Email_Index.csv`: one row per email with its reference, page in the bundle, quote and attachments. Opens in Excel.
- `Native_Files/<ref>/`: attachments that can't go in a PDF (spreadsheets, Word files, damaged or password-protected PDFs). The email's header block says where each one is.

Open the bundle and check a few emails against their bookmarks before handing over. Share only the `share/` folder.

### 10. Draft the handoff email

Follow `reference/handoff-email.md`. Show the draft in chat with placeholders for the requester's name, the file links and the sender's name. Do not send it.

## When things go wrong

- **Batch still short after retry:** list its message ids as "Unclassified, needs manual review". Never drop them.
- **Unreadable attachment:** a corrupt PDF or unsupported format leaves the text empty. Report it as "attachment present, not machine-readable". It is still copied into `flagged_emails/` if its message is flagged.
- **Boilerplate matches:** email disclaimers ("may not be copied without the author's permission") produce false hits on words like "permission". The classification prompt tells sub-agents to ignore them. If the findings are still full of them, narrow the keyword list.
- **Missing image evidence:** check `decorative: true` rows in `attachment_text.jsonl`. The size threshold for skipping images (15 KB) can catch a small screenshot.

## Testing

`uv run scripts/test_share_pack.py` runs ingest, collect and the share pack on a synthetic mailbox (HTML email with an inline image, PDF and spreadsheet attachments, a damaged PDF) and checks the output. Pass a folder path to keep the output for a look.

`examples/sample.mbox` is a synthetic five-message mailbox with a thread, a duplicate attachment, a calendar invite and an auto-reply. Regenerate it with `python3 scripts/generate_fixture.py`.
