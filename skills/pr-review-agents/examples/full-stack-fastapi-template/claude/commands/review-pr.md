---
allowed-tools: Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)
description: Review a pull request for FastAPI backend and React frontend changes
---

Perform a comprehensive FastAPI and React full-stack code review using subagents for key areas:

- code-quality-reviewer
- performance-reviewer
- test-coverage-reviewer
- documentation-accuracy-reviewer
- security-code-reviewer

Instruct each to only provide noteworthy feedback. Once they finish, review the feedback and post only the feedback that you also deem noteworthy.

Pay special attention to:
- Authorization on new or modified endpoints: `CurrentUser` or `get_current_active_superuser` from `backend/app/api/deps.py`, plus the owner-or-superuser check used in `backend/app/api/routes/items.py`
- API contract drift: a change to a route or to a `*Public`/`*Create`/`*Update` model in `backend/app/models.py` must come with a regenerated `frontend/src/client/` (via `scripts/generate-client.sh`) and matching frontend usage
- Migration safety: every change to a `table=True` model in `backend/app/models.py` needs an Alembic revision in `backend/app/alembic/versions/` with a correct `down_revision` chain and a working `downgrade()`
- The dev-only `private` router (`backend/app/api/routes/private.py`, included only when `FASTAPI_ENV == "development"` in `backend/app/api/main.py`) creates users with no authentication for the Playwright tests, so it must never become reachable outside development
- Secrets and settings: new settings belong in `Settings` in `backend/app/core/config.py`, secrets go through the `changethis` check, and the tracked `.env` holds only local defaults
- Generated files are not hand-edited: `frontend/src/client/`, `frontend/src/routeTree.gen.ts` and `backend/app/email-templates/*.html` (generated from `packages/react-email/`)
- Dependency changes to `pyproject.toml` or `uv.lock` are restricted to organization members (`CONTRIBUTING.md`, `.github/workflows/guard-dependencies.yml`)

Provide feedback using inline comments for specific issues.
Use top-level comments for general observations or praise.
Keep feedback concise.
