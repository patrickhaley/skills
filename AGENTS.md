# AGENTS.md

This is a public repo of personal skills, commands, prompts and workflows for AI tools. Anything committed here is visible to the world.

## Privacy (check before every commit)

Never commit:

- Secrets: API keys, tokens, passwords, connection strings, `.env` files
- Personal info: names of real people, email addresses, phone numbers, home or office addresses
- Employer or client details: company names, internal system names, internal URLs, ticket or project IDs, customer data
- Machine-specific paths that reveal usernames (use `~/` or placeholders instead)
- Anything copied from private or internal repos

If a skill needs an example, use generic placeholders (`example.com`, `Jane Doe`, `ACME`). If you're unsure whether something is private, leave it out and ask.

Before committing, review the full diff (`git diff --staged`) for any of the above.

## Structure

- One folder per skill: `skills/<skill-name>/SKILL.md`
- Folder names are lowercase kebab-case and match the `name` in frontmatter
- Supporting files (scripts, references, templates) live inside that skill's folder
- Example GitHub Actions workflows live in `github-actions/<group>/<group>-<name>.yml` (for example `claude/claude-mentions.yml`). The filename prefix matches the folder so files stay grouped when copied into a flat `.github/workflows/`. List each one, with its required secrets, in `github-actions/README.md`. They are reference copies for other repos. Never put them in `.github/workflows/`, which would make them run in this repo.

## GitHub Actions examples

Before committing a workflow, also check that:

- Secrets are referenced only as `${{ secrets.NAME }}` and use generic names (for example `ANTHROPIC_API_KEY`, not one tied to an employer)
- It contains no org or repo names, runner labels, internal registries, or internal URLs
- Third-party actions are pinned to a version tag or commit SHA

## SKILL.md format

Every `SKILL.md` starts with YAML frontmatter:

```yaml
---
name: skill-name
description: What it does and when to use it, in one or two sentences.
---
```

Keep skills tool-agnostic where practical, and write instructions in plain, direct language.

### When to add `disable-model-invocation: true`

This flag stops the agent from loading the skill on its own. The skill then only runs when the user calls it by name (for example `/skill-name`).

Add it when the skill:

- Is heavy or long-running (multi-step harnesses, big workflows) and would be costly to trigger by mistake
- Takes actions with side effects: committing, pushing, publishing, sending messages, deleting or changing data
- Changes how the whole session runs (process overhauls, strict modes) rather than helping with one task
- Has a description broad enough that it could match unrelated requests

Leave it off when the skill is lightweight reference or know-how that should load whenever it's relevant (formatting conventions, how to use a tool, domain knowledge).

If unsure, add the flag. A skill that needs to be called by name is a smaller problem than one that fires when it shouldn't. If you add it, say so in the description too (for example "Use only when the user asks for /skill-name").

## README

When adding, renaming or removing a skill, update the list in `README.md`.

## Commits

- Short, imperative commit messages (for example, "Add task-harness skill")
- One skill or change per commit
- Don't commit or push unless asked
