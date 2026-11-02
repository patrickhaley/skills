# manifest.jsonl / attachment_text.jsonl schema

One JSON object per line.

## manifest.jsonl (one row per message)

| field | type | notes |
|---|---|---|
| message_id | string\|null | RFC 822 Message-Id header |
| in_reply_to | string\|null | |
| references | string\|null | |
| index | int | position in the source mbox |
| date | string (ISO 8601)\|null | parsed from the Date header |
| date_raw | string\|null | original Date header, kept for audit |
| from / to / cc | string\|null | raw header values |
| subject | string | |
| body_text | string | text/plain preferred, text/html stripped as fallback |
| attachment_hashes | list[string] | sha256 of each attachment on this message |
| thread_id | string | root Message-Id of the thread, or a normalized-subject key if headers were absent |
| is_noise | bool | see noise-patterns.md |
| noise_reason | string\|null | one of: auto_reply, auto_reply_or_bounce, bounce, calendar_invite |

## attachment_text.jsonl (one row per UNIQUE attachment, by hash)

| field | type | notes |
|---|---|---|
| hash | string | sha256, matches manifest.jsonl's attachment_hashes entries |
| filename | string | first filename seen for this hash |
| kind | string | pdf \| zip \| image \| other |
| text | string | pdftotext output (pdf), newline-joined filenames (zip), OCR text (image, once recorded), or "" |
| needs_ocr | bool | true until record_ocr.py has been run for this hash; always false for images tagged `decorative` |
| decorative | bool | image-only heuristic (see noise-patterns.md) for email-signature icons/logos never worth OCR'ing; false for all non-image kinds |
| path | string | path to the deduped stored file |
