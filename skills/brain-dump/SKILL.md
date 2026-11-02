---
name: brain-dump
description: Turn a raw brain dump (notes, ideas, conversation fragments) into a structured outline that keeps the original wording, then a summary with action items and follow-ups. Use only when the user asks for /brain-dump.
disable-model-invocation: true
---

# Brain dump

Take the raw text the user gives you and produce two outputs, in order: a structured outline, then a summary and action plan built from that outline.

If the user calls the skill without any text, ask them to paste it.

## Title

Start the output with a title that begins with a date in `YYYY-MM-DD` format. Use the event date if the text gives one. Otherwise use today's date. For example: `2026-10-30 Messy brain dump notes now organized`.

## Part 1: Organized outline

Your role here is purely structural.

- **Keep the original content.** Keep the voice, tone and exact phrasing.
- **Don't edit or add.** Don't rewrite sentences, fix grammar, or add new ideas or interpretations.
- **Impose order.** Group related points, put topics in a logical sequence, and use headings and nested bullets to show the hierarchy.
- **Flag ambiguity.** If a point is unclear or incomplete, don't fix it. Add `(unclear)` to the end of that point.

The result is a clean outline of the original content, not a new draft.

## Part 2: Summary and action plan

Work from the Part 1 outline and write a concise, professional summary in exactly this format:

```markdown
**Main Topics:**
- [Primary themes or categories in the text]

**Summary by Topic:**
- **[Main Topic 1]:** [Essential points, open questions and any conclusions on this topic]
- **[Main Topic 2]:** [...]

**Key Takeaways:**
- [Most important insights or conclusions]

**Action Items:**
- **[Task description]:** Owner: [Name, team, or "me"], Deadline: [Date or timeframe]

**Follow-Up Actions:**
- [Unresolved questions that need answers]
- [Suggested next steps or items to address later]
```

If the text doesn't name an owner or deadline, write "Not stated" rather than guessing.
