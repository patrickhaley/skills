# Report template

Post the report in chat and save it to:

    <case-dir>/<case-slug>-ediscovery-report-<YYYY-MM-DD>.md

`<case-slug>` is the case name from the pre-flight questions. The date is
the day the report is generated, not the corpus dates. If a file with that
name already exists (for example, a rerun on the same day), add `-v2`,
`-v3` and so on rather than overwriting it.

## Facts only, no legal advice

The report presents what the emails say, with dates and quotes. The
requester and their advisers draw the conclusions.

- Describe what was said and when. Do not say what it means legally.
- Do not use conclusion words such as "breach", "liable", "valid consent",
  "binding", "waived", "admission" or "in violation", unless you are quoting
  an email.
- Do not treat silence as agreement. Write "no reply found in this export".
- Do not assess the strength of anyone's position, and do not recommend
  next steps, legal strategy or what to do with the findings.
- Where a quote is ambiguous, say so and show it in full. Do not pick a
  reading.
- The report covers this export only. Say "not found in this export", never
  "never happened".

## Structure

    # eDiscovery review: <case name>

    > Factual summary of the emails in this export. It is not legal advice
    > and draws no conclusions about anyone's rights, obligations or
    > liability. Emails outside this export were not reviewed.

    **Generated:** <YYYY-MM-DD>
    **Source:** <mbox filename>, <first date> to <last date>
    **Scope:** <date range used>, <excluded senders or "none">
    **Keywords:** <approved keyword list>
    **Templates:** <selected analysis templates>

    ## Chronological timeline
    (Timeline template only. Every flagged event in date order: date |
    from | to | quote. Note the earliest mention by each party.)

    ## Requests and replies
    (Requests template only. Table: date | requester | recipient | request
    quote | reply date | reply quote, or "no reply found in this export".)

    ## Acknowledgements and related statements
    (Acknowledgements template only. Table: date | acknowledgement quote |
    date | related later statement quote. Place them side by side without
    saying whether they conflict.)

    ## Custom question
    (Custom template only. The relevant quotes with dates, in date order. If
    the question asks for a conclusion, present the quotes and leave the
    conclusion to the requester.)

    ## Coverage and exclusions
    - Messages ingested: <N>
    - Tagged as noise: <N> (calendar invites <n>, auto-replies <n>, bounces <n>)
    - Out of scope (date range or excluded senders): <N>
    - Classified: <N> in <N> batches
    - Unclassified after retry: <N>, listed by message id for manual review
    - Images not OCR'd: <N>, and why
    - Attachments present but not machine-readable: <N>, listed
    - Flagged as relevant: <N>

    ## Flagged emails
    Each flagged email is in <Case>_Email_Bundle.pdf, in date order, with
    its attachments. <Case>_Email_Index.csv lists them with page numbers.

## Rules

- Every finding cites a date, the participants and a direct quote.
- Cite emails by message id (`idx-<N>`). The share pack turns these into
  "Email 0001 (bundle p. 5)" in the Word copy.
- If a selected template finds nothing, keep its section and say so ("No
  requests found in this export"). A missing section reads as "not checked".
- Leave out sections for templates that were not selected.
