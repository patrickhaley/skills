# Default noise filtering

Applied automatically during ingest.py; tagged (`is_noise: true`, with a
`noise_reason`), never deleted, and always counted in the final report so
nothing disappears silently.

| noise_reason | trigger |
|---|---|
| auto_reply | `Auto-Submitted` header present and not "no" |
| auto_reply_or_bounce | Subject starts with "Automatic reply:", "Out of Office", "Undeliverable:", or "Delivery Status Notification" (case-insensitive) |
| bounce | From address contains "mailer-daemon" or "postmaster" |
| calendar_invite | Message contains a `text/calendar` MIME part |

Not currently auto-detected (flag manually via a custom keyword/question if
relevant to a case): pure marketing/newsletter blasts with no custodian
authorship. These didn't reliably distinguish from legitimate forwarded
business content in testing, so they're left for the classification pass
rather than a blind header/subject rule that could suppress real evidence.

## Decorative images (never sent for OCR)

`ingest.py` also tags image attachments as `decorative: true` (and sets
`needs_ocr: false`) when either is true:

- **Filename pattern** matches common signature/social-icon conventions
  (`opensense`, `outlook-image`, `social-icon`, `email-icon`, `cell-icon`,
  `address-icon`, `direct-icon`, or a bare `image00N.png`/`.gif`).
- **File size** is under 15KB — small enough to almost certainly be an
  inline logo or icon rather than a photo, screenshot, or scanned document.

Like noise tagging, this only skips OCR — it never deletes the attachment or
excludes its parent message from classification. In testing on a real
mailbox this cut a ~360-image OCR queue by roughly 40% (signature icons,
Outlook inline logos) with no loss of substantive content. If a case seems
to be missing image evidence, check `attachment_text.jsonl` for `decorative:
true` rows and spot-check a few — the size threshold in particular is a
blunt instrument and could in principle catch a small-but-substantive image
(e.g. a tightly-cropped screenshot).

## Boilerplate keyword matches during classification

Standard corporate email-forwarding/confidentiality disclaimers (e.g. "may
not be copied or sent to any other recipient without the author's
permission") appear on nearly every forwarded message in a typical corporate
mailbox and will otherwise swamp a "permission"/"consent"/"authorize"
keyword with false positives — in testing on a real mailbox this was the
single largest source of noise in classification findings. the
`workflow_classify.js` prompt explicitly instructs sub-agents to disregard this kind
of boilerplate and only mark a message relevant when the keyword is used
substantively (a real request or reply). If a case's findings still
look boilerplate-heavy, consider narrowing the approved keyword list itself
rather than relying solely on the prompt instruction.
