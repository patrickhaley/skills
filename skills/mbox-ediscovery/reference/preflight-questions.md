# Pre-flight questions

Ask these after ingest and before OCR or classification. Use
`AskUserQuestion` when it is available, otherwise ask in plain text. It takes
at most four questions per call and four options per question, so ask in two
rounds.

Before asking, pull the context the questions need from `manifest.jsonl`: the
earliest and latest dates, and the most frequent From/To/Cc addresses with
message counts.

## Round 1: scope

1. **Case name.** Becomes the case slug in folder and report names
   (lowercase kebab-case). Offer one derived from the mbox filename as the
   recommended option; the user can type their own.
2. **Date range.** Show the detected first and last dates. Options: "Full
   range (recommended)" or "Narrow it" (then ask for start and end dates as
   YYYY-MM-DD).
3. **Senders to exclude.** Options: "Keep everyone (recommended)" or
   "Exclude some". If they exclude, show the top addresses by count in plain
   text and ask which to drop. Shared aliases and system senders are the usual
   candidates.

## Round 2: what to look for

4. **Seed keywords or topics.** Free text, comma-separated.
5. **Analysis templates** (multi-select; pick one or more):
   - Chronological timeline (first mention vs. first discovery)
   - Requests and replies (for example, someone asking for permission)
   - Acknowledgements and related later statements
   - Custom question (ask for the question as a follow-up; if it asks for a
     legal conclusion, such as "did they breach the agreement?", say the
     report will show the relevant emails but not the conclusion)

## Then: keyword expansion

Expand the seed keywords into synonyms, likely variants and misspellings,
and related terms. Scan the manifest subjects and bodies for proper nouns,
domains and nicknames to seed this. Show the full list in plain text, then
ask the user to approve it as is, or to say what to add or remove. Do not
classify anything until the list is approved.
