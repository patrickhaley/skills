# Skills by @patrickhaley

My personal collection of skills, commands, prompts and workflows for AI tools.

I'm building these in public and sharing them in case they're useful to someone else. Anything private stays in private or internal repos.

## What's here

- [`skills/`](skills/) – one folder per skill, each with a `SKILL.md`

- [`mbox-ediscovery`](skills/mbox-ediscovery/SKILL.md) – reviews an mbox email export for a legal or eDiscovery question and produces a cited, facts-only report
- [`pr-review-agents`](skills/pr-review-agents/SKILL.md) – installs a multi-agent Claude PR review tailored to a repo's stack
- [`task-harness`](skills/task-harness/SKILL.md) – runs a multi-step task through a plan, evidence-based checks and handoff files instead of one long chat

- [`github-actions/`](github-actions/) – example GitHub Actions workflows to copy into other repos (they don't run here)

## Using them

In Claude Code, install them all as a plugin:

```
/plugin marketplace add patrickhaley/skills
/plugin install patrick@patrickhaley
```

Skills are then available as `/patrick:<skill-name>`. Run `/plugin marketplace update patrickhaley` to pick up changes.

For other tools, copy any skill folder into the tool's skills directory and adapt it to suit.

No guarantees. Use, fork and remix freely.
