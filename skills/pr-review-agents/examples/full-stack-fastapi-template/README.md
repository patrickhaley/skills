# Example: full-stack-fastapi-template

This is the output of running `/pr-review-agents` against [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) (MIT) at commit `f4bcfab` (2026-10-26). That repo has a FastAPI + SQLModel + Postgres backend, a React + Vite frontend, Alembic migrations, pytest and Playwright.

It is here to show the level of detail a filled-in set should have. The upstream project doesn't use it.

| File here | Installed at |
| --- | --- |
| `github/workflows/claude-pr-review.yml` | `.github/workflows/claude-pr-review.yml` |
| `claude/commands/review-pr.md` | `.claude/commands/review-pr.md` |
| `claude/agents/*.md` | `.claude/agents/*.md` |
| `AGENTS.md` | `AGENTS.md` (the repo had none, so it only holds the "keep it current" note) |

Compare any file with its template in `../../template/` to see what changed. Only the `FILL:` regions should differ.
