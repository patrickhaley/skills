---
name: pr-review-agents
description: Install or refresh a multi-agent Claude PR review (a GitHub Actions workflow, a /review-pr command and five reviewer subagents) tailored to the current repo by discovering its stack and conventions. Use only when the user asks for /pr-review-agents.
disable-model-invocation: true
---

# PR review agents

Sets up an automated PR review in the current repo:

- `.github/workflows/claude-pr-review.yml` runs on each new PR. It rewrites the PR summary, then runs `/review-pr`.
- `.claude/commands/review-pr.md` sends the PR to five reviewer subagents and posts only the findings it also judges noteworthy.
- `.claude/agents/` holds the five reviewers: code quality, performance, test coverage, documentation accuracy and security.

The output stays consistent from repo to repo because the reviewer roster, the "noteworthy only" filter and each reviewer's output format are fixed. Only the checklists change: what each reviewer looks for in this particular repo. Those come from discovery, never from another repo's copy.

## Modes

- `/pr-review-agents` installs into the current repo.
- `/pr-review-agents refresh` updates an existing install after the repo has changed.

If the files already exist and the user didn't say `refresh`, ask which they want. Never silently overwrite a filled-in set.

## Template

The template is in `template/` next to this file, with no leading dots so it never runs where it's stored:

| Template | Installs to |
| --- | --- |
| `template/github/workflows/claude-pr-review.yml` | `.github/workflows/claude-pr-review.yml` |
| `template/claude/commands/review-pr.md` | `.claude/commands/review-pr.md` |
| `template/claude/agents/*.md` | `.claude/agents/*.md` |

Repo-specific parts are marked `<!-- FILL: name ... -->`, with guidance inside the marker. **Everything outside a FILL marker is fixed. Copy it verbatim.** If something fixed looks wrong for this repo, raise it with the user instead of editing it.

A filled-in example made from a public repo is in `examples/`. Use it to judge the level of detail. Never copy facts from it.

## Install

### 1. Discover

Build a picture of the repo from evidence. If you can run subagents, split this by area. Read:

- **Agent instructions:** `AGENTS.md`, `CLAUDE.md` (all levels) and contributing guides. Treat the repo's own stated rules as authoritative. Instruction files that belong to dependencies (vendored, symlinked into `.venv`/`node_modules`, or plugin skills) are not this repo's conventions.
- **Layout:** the directory tree to about three levels, and whether it's a monorepo. List the apps, services, packages, charts or environments.
- **Stack:** manifests and lockfiles (`package.json`, `pom.xml`, `build.gradle`, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Chart.yaml`, `*.tf` and so on), with versions of the main frameworks.
- **Patterns:** open two or three representative units of each kind (a feature, an endpoint, a component, a migration, a chart) and note how they're built and named.
- **Data:** ORM or query layer, migrations, caches and queues.
- **Auth:** search for the auth provider, middleware, guards, permission checks and how tokens are handled.
- **Tests:** frameworks, test locations and naming, fixtures and mocks, and what CI runs.
- **Docs:** README(s), `docs/`, API docs and env var references.
- **Tooling:** linters, formatters and existing CI workflows (`.github/workflows/`). Note any workflow linter or security scanner (actionlint, zizmor) and the repo's conventions for actions (SHA pinning, `persist-credentials`, timeouts), because the installed workflow has to pass them.
- **Exposure:** whether the repo is public (`gh repo view --json visibility`) and whether it takes outside contributions (CONTRIBUTING, fork PRs in history). See [Security notes](#security-notes).
- **Change history:** `git log --oneline -50` and, if `gh` works, `gh pr list --state merged --limit 30`. These show which kinds of change are common, which drives the PR summary categories.

Write down what you found as a short table: *area · evidence (paths) · conclusion*. Mark anything you couldn't establish as **unknown**. Don't guess.

### 2. Fill

Copy the template to the install paths, then replace every FILL marker following its guidance. Rules:

- **Every checklist bullet must be about this repo.** Name a real path, package, class, config key, command or documented rule, and confirm it exists with Glob or Grep before writing it. Add a generic best-practice bullet only when it clearly applies to this stack.
- **Keep all five reviewers.** Reinterpret them for the repo instead of dropping one. In an infrastructure repo, test coverage means validation (lint, template rendering, plan, policy checks) and performance means resource sizing.
- **Use the repo's own words.** If AGENTS.md calls something a "feature module", so does the checklist.
- **Unknowns stay out of the checklists.** List them for the user instead.
- If the user offers another repo's filled-in set as a starting point, use it for tone and level of detail only. Every fact has to come from this repo's discovery.

### 3. Verify

Run these and fix anything they turn up:

```bash
# No markers left
grep -rn 'FILL:' .claude/agents .claude/commands/review-pr.md .github/workflows/claude-pr-review.yml

# Every backticked path in the agents and command exists (globs and placeholders aside)
grep -ohE '`[A-Za-z0-9_./*-]+/[A-Za-z0-9_./*-]*`' .claude/agents/*.md .claude/commands/review-pr.md \
  | tr -d '`' | sort -u | while read -r p; do compgen -G "$p" >/dev/null || echo "missing: $p"; done

# Workflow syntax, if actionlint is installed
actionlint .github/workflows/claude-pr-review.yml
```

Check that only FILL regions changed. `scripts/check_fixed.py` (next to this file) takes template/installed pairs:

```bash
S=<path to this skill>
args=(); for f in "$S"/template/claude/agents/*.md; do args+=("$f" ".claude/agents/$(basename "$f")"); done
python3 "$S/scripts/check_fixed.py" "${args[@]}" \
  "$S/template/claude/commands/review-pr.md" .claude/commands/review-pr.md \
  "$S/template/github/workflows/claude-pr-review.yml" .github/workflows/claude-pr-review.yml
```

Limits of the path check:
- It only sees backticked tokens containing a `/`. Spot-check bare filenames and paths in the workflow's summary categories by hand.
- Generated or gitignored paths (build output, generated clients) show up as missing even when the statement is true. Confirm with the repo's `.gitignore` or build config, and reword (for example "build output in `x/`, not committed") instead of deleting a correct check.

If the repo lints its workflows (actionlint config, zizmor, a pre-commit hook), run the same tools against the new workflow. If the fixed text fails them, don't edit it. Report it (step 5).

### 4. Keep it current

Add this to the repo's `AGENTS.md`, or `CLAUDE.md` if that's what it uses. If neither exists, ask before creating `AGENTS.md`, because a new top-level file is a visible change. The documentation reviewer's checklist assumes this file exists, so settle this before filling that checklist.

```markdown
## PR review agents

`.claude/agents/*-reviewer.md`, `.claude/commands/review-pr.md` and
`.github/workflows/claude-pr-review.yml` describe this repo's stack and conventions. When a
change alters the stack, folder layout, auth, data layer, test setup or documented
conventions, update them in the same PR, or run `/pr-review-agents refresh`.
```

### 5. Report

Tell the user:

- the discovery table, with any unknowns
- the files written
- anything in the fixed template text that conflicts with this repo (its workflow linters, action conventions, PR title conventions), so the user can decide whether to diverge or fix the template
- the cost-related defaults they may want to change: `--model opus`, `track_progress: true`, and a review on every non-draft PR
- whether the repo is public or takes outside contributions, with the recommendation from [Security notes](#security-notes)
- setup still needed: install the Claude GitHub App on the repo, add an `ANTHROPIC_API_KEY` Actions secret, and merge to the default branch (a `workflow_dispatch` trigger only works once it's there)
- how to test: run the workflow manually against an existing PR number and read the review

Don't commit or push unless the user asks.

## Refresh

1. Read the installed files. Treat hand edits as intentional.
2. Re-run discovery, focusing on what goes stale: renamed or deleted paths, added or removed dependencies and frameworks, new top-level folders, changed auth or test setup, and new rules in AGENTS.md or CLAUDE.md.
3. Run the path check from Install step 3 against the installed files to find broken references.
4. Compare the fixed parts with the current template. If the template has changed (for example a newer action pin or wording), list those changes separately.
5. Show the proposed edits grouped by file, with stale items, new items and template updates kept separate. Apply them once the user agrees.
6. Make sure the "Keep it current" note from Install step 4 is present.

## Security notes

- Fork PRs don't receive secrets, so the review only runs on branches in the same repo.
- The PR diff and body are untrusted input to a model that can run `gh pr edit` and `gh pr comment`. That's acceptable for repos where contributors are trusted. For repos open to outside contributors, narrow the allowed tools in the workflow before enabling it, or don't install it.
- The reviewers have `WebFetch` and `WebSearch` so they can check documentation and cite references. A prompt injection in a diff could use them to send repo content to an outside URL. That is a deliberate tradeoff for trusted-contributor repos. Remove both tools from `tools:` in repos where it isn't.
