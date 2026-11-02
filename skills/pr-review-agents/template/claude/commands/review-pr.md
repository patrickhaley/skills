---
allowed-tools: Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)
description: Review a pull request for <!-- FILL: stack-short — a noun phrase that also fits "a comprehensive ___ code review" below, e.g. "Angular frontend", "Java backend", "infrastructure" --> changes
---

Perform a comprehensive <!-- FILL: stack-short --> code review using subagents for key areas:

- code-quality-reviewer
- performance-reviewer
- test-coverage-reviewer
- documentation-accuracy-reviewer
- security-code-reviewer

Instruct each to only provide noteworthy feedback. Once they finish, review the feedback and post only the feedback that you also deem noteworthy.

Pay special attention to:
<!-- FILL: focus-areas
4-8 bullets. These are the cross-cutting, highest-risk things in THIS repo: the rules a
newcomer most often breaks, or the changes with the widest blast radius. Each bullet names a
real convention, path, package or config key, e.g.
- Cross-package impact (changes to `packages/shared-*` affect every app)
- Migration safety (ordering, backward compatibility, shared schema)
- Authorization on new or modified endpoints (`@RequiresRole` on every controller method)
Pull them from AGENTS.md/CLAUDE.md rules, architecture docs, and the risks discovery found.
-->

Provide feedback using inline comments for specific issues.
Use top-level comments for general observations or praise.
Keep feedback concise.
