---
name: task-harness
description: Run a multi-step task through a plan, evidence-based checks, and handoff files instead of one long chat. Use only when the user explicitly asks for the harness or /task-harness.
disable-model-invocation: true
---

# Task harness

Use this for work big enough to span several steps or sessions. Do not use it for anything that fits in one short session. The point is that the plan, the checks, and the handoff live in files, so the result does not depend on one long conversation.

## 1. Confirm the inputs

Collect these six, in this order:

1. Task
2. Deliverable and output path
3. Acceptance checks (how we will know it is done)
4. Source material
5. Allowed changes (scope)
6. Run limit (time, steps, or attempts)

First fill in whatever the request already gives you. Then ask about each missing input, one question at a time, and wait for the answer before asking the next. Use `AskUserQuestion` when it is available, and put a recommended option first when you can infer one (scope from the repo layout, or a limit of three attempts per step, for example). Otherwise ask in plain text.

If the acceptance checks are vague ("make sure it works"), push back and propose two or three checks that can be run or observed. Do not accept a check you cannot verify.

Once all six are filled, read them back as a short list and get a yes before moving on. Do not enter plan mode until then.

## 2. Preflight

- Read the project instructions (`CLAUDE.md` or `AGENTS.md`) and inspect the current state of the work before editing anything.
- Keep every edit inside the allowed scope.
- Anything that must hold every time (format, lint, type check, blocked paths) belongs in a hook, script, or settings rule, not in this prompt. If one is missing, say so, offer to add it, and list it in `CLAUDE.md` OR `AGENTS.md` once it exists. Do not rely on remembering a deterministic rule.
- Ask before publishing, sending, filing, or spending. Anything that changes data comes back as a draft first.
- Never let two sessions edit the same file.
- Before any risky change, save a recoverable version (a commit or a copy).

## 3. Plan, then pause

Enter plan mode. Write `PLAN.md` as numbered steps. Each step has one output and one check, names the files it reads and writes, and is marked if it can run in parallel with others. Write the checks before the work, not after. Save plan.md and stop for approval before any edit.

## 4. Execute

Loop until the work is complete, a blocker appears, or the run limit is reached.

1. Read `PLAN.md` and pick the next ready steps.
2. Run independent steps in parallel as subagents. Give each one only its step, its inputs, and its check.
3. Keep long logs and raw output out of the main session. Subagents return paths, verdicts, and evidence.
4. Verify every output against its check (see section 5).
5. Send failed steps back individually, never the whole batch.
6. Merge accepted outputs and run the full checks on the merged result.

Do not weaken a check to get a pass.

## 5. Verify with real signals

Tests, builds, type checks, screenshots, and the actual output count as evidence. Confidence does not. Save `CHECKS.md` with one row per requirement:

| step | requirement | verdict | evidence |
|---|---|---|---|

Verdict is pass, fail, or unresolved. Leave missing evidence visible rather than filling the gap.

## 6. Feedback

- **Correction:** a failed check sends that step back with the reason, the evidence, and the scope "fix this step only". Cap it at three attempts, then mark the step unresolved and surface it.
- **Memory:** when you catch a mistake or the user corrects you, draft the rule for `CLAUDE.md` or `AGENTS.md` so the next session does not repeat it. Only add rules that will apply again, and show the diff before saving.

## 7. Handoff

After each stage, update `PROGRESS.md` with:

- **Plan:** steps done, running, and blocked
- **Outputs:** exact paths to the current saved files
- **Decisions:** what changed in the harness and why
- **Open issues:** failures, uncertainties, blockers
- **Next action:** the next ready step

On resumption, read `CLAUDE.md` or `AGENTS.md`, `PLAN.md`, and `PROGRESS.md` first, then continue from the recorded next action.

## 8. Finish

Before calling it done, confirm that every output exists and opens, every check ran against the saved version, failures are fixed or reported, and `CLAUDE.md` or `AGENTS.md` has every new rule from the run.

Return the deliverable, `PLAN.md`, `CHECKS.md`, `PROGRESS.md`, and the `CLAUDE.md` or `AGENTS.md` diff. State what was checked, what passed, and what remains unresolved. If a limit or blocker stopped the run, return a partial status listing the exact steps left. Report usage figures only if they were measured, and never estimate savings.
