# github-actions

Example GitHub Actions workflows to copy into other repos. They don't run here: GitHub only runs workflows in `.github/workflows/`, and nothing in this folder lives there.

None of these belong in every repo. Pick the ones that fit.

## What's here

Workflows are grouped by folder, and every file starts with its folder name. `.github/workflows/` can't have subfolders, so the prefix is what keeps them grouped once copied.

| Workflow | What it does | Needs |
| --- | --- | --- |
| **claude/** | | |
| [`claude-mentions.yml`](claude/claude-mentions.yml) | Responds to `@claude` in issues, PRs and review comments (repo members only) | `ANTHROPIC_API_KEY` |
| [`claude-issue-triage.yml`](claude/claude-issue-triage.yml) | Labels new issues using the repo's existing labels. Never comments | `ANTHROPIC_API_KEY` |
| **jira/** | | |
| [`jira-link-pr.yml`](jira/jira-link-pr.yml) | Adds the Jira issue summary to a PR, keyed from the PR title. *Reusable* | `JIRA_API_TOKEN` |
| [`jira-deployment-signal.yml`](jira/jira-deployment-signal.yml) | On merge, records a GitHub deployment and links it to the Jira issue. Deploys nothing. *Reusable* | `JIRA_API_TOKEN` (+ optional `JIRA_API_EMAIL`) |
| **lint/** | | |
| [`lint-pr-title.yml`](lint/lint-pr-title.yml) | Fails PRs whose title isn't a Conventional Commit, and explains why in a comment | — |
| [`lint-workflows.yml`](lint/lint-workflows.yml) | Runs actionlint on `.github/workflows/` | — |
| [`lint-claude-plugins.yml`](lint/lint-claude-plugins.yml) | Validates a Claude Code plugin marketplace and its plugins | — |
| **release/** | | |
| [`release-please.yml`](release/release-please.yml) | Opens release PRs and cuts tags/releases from Conventional Commits | `RELEASE_APP_ID`, `RELEASE_APP_PRIVATE_KEY` |

Workflows marked *Reusable* use `on: workflow_call` and need a small caller workflow (see below).

## Deploying one

1. Copy the `.yml` file into the target repo's `.github/workflows/`, keeping its name.
2. Add the secrets from the table under **Settings → Secrets and variables → Actions**.
3. Read the comments at the top of the file and adjust triggers, branches and paths.
4. Open a PR. If you've also copied `lint-workflows.yml`, it checks the new file.

Third-party actions are pinned to commit SHAs (with the version in a comment). GitHub's own `actions/*` stay on major tags. To keep the pins current, enable Dependabot for the `github-actions` ecosystem in the target repo.

### Claude

- Install the Claude GitHub App on the repo, or run `/install-github-app` in Claude Code, which also sets the secret.
- `claude-issue-triage.yml` only applies labels that already exist, so create your labels first.
- `claude-issue-triage.yml` lets anyone who can open an issue trigger it. On a public repo, that's anyone. Claude itself can't change anything: it only suggests labels, and a separate step applies the ones that exactly match existing labels.

### Jira

Both are reusable workflows. Copy the file, then add a caller in the same repo:

```yaml
# .github/workflows/jira.yml
name: Jira
on:
  pull_request:
    types: [opened, edited, synchronize, closed]
    branches: [main]

jobs:
  link-pr:
    if: github.event.action != 'closed'
    uses: ./.github/workflows/jira-link-pr.yml
    with:
      jira-base-url: https://your-domain.atlassian.net
      issue-regexp: 'ABC-\d+'
    secrets:
      JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}

  deployment-signal:
    if: github.event.action == 'closed'
    uses: ./.github/workflows/jira-deployment-signal.yml
    permissions:
      contents: read
      deployments: write
    with:
      jira_base_url: https://your-domain.atlassian.net
      issue_regexp: 'ABC-[0-9]+'
      branch_environments: |
        main:prod
    secrets:
      JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
```

If several repos use them, host them once in a shared repo's `.github/workflows/` and point `uses:` at `<owner>/<shared-repo>/.github/workflows/<file>.yml@<tag>`. Callers then pick up fixes by bumping a tag instead of re-copying files.

Note the two files use different regexp dialects: JavaScript (`\d+`) for `jira-link-pr.yml` and POSIX (`[0-9]+`) for `jira-deployment-signal.yml`.

### Conventional Commits and releases

`lint-pr-title.yml` and `release-please.yml` are designed as a pair. With squash-merge, the PR title becomes the commit message, and release-please reads it to decide version bumps. `lint-pr-title.yml` also works on its own.

`release-please.yml` needs:

- A GitHub App with **Contents** and **Pull requests** set to read/write, installed on the repo. Store its ID and private key as `RELEASE_APP_ID` and `RELEASE_APP_PRIVATE_KEY`. The file's header comment explains why it doesn't use `GITHUB_TOKEN`.
- Two files at the repo root. The minimal single-package setup is `release-please-config.json`:

  ```json
  { "packages": { ".": { "release-type": "simple" } } }
  ```

  and `.release-please-manifest.json`:

  ```json
  { ".": "0.1.0" }
  ```

  For other release types and monorepos, see the [release-please docs](https://github.com/googleapis/release-please).

### Lint

- `lint-workflows.yml` is worth adding to any repo that has workflows.
- `lint-claude-plugins.yml` is only for Claude Code plugin marketplace repos (`.claude-plugin/` plus `plugins/<name>/`).
