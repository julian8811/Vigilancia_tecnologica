# Contributing to VigilaGraph IA

Thanks for your interest in contributing. This document covers the workflow, conventions, and review process.

## Quick links

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Security policy](SECURITY.md)
- [Architecture docs](docs/ARCHITECTURE.md)

## Workflow

We use a **stacked-PR** workflow on top of `main`:

1. Cut a feature branch from `main`: `git switch -c feat/<short-name>`
2. Develop and commit (conventional commits — see below).
3. Push and open a PR targeting `main`.
4. After review, the maintainer merges via squash.

> **Stacked PRs.** If your change logically splits into 2+ reviewable units (e.g. backend model + frontend page), prefer two separate PRs. Avoid stacking more than ~400 lines in a single PR; reviewers will ask you to split.

## Commit message format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short summary>

<optional body — explain the *why*>

<optional footer — references to issues, breaking changes>
```

Allowed types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`.

Examples:

```
feat(auth): add refresh-token endpoint
fix(graph): clamp cytoscape zoom to container bounds
docs(readme): correct architecture diagram
ci(github): add pip-audit step to security job
```

## Code style

### Python (`api/`)

- **Formatter / linter:** `ruff format` + `ruff check` (configured in `api/pyproject.toml`).
- **Types:** `mypy --ignore-missing-imports` (strict mode is a roadmap item).
- **Naming:** `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for constants.
- **Imports:** absolute only. No relative imports crossing package boundaries.

### TypeScript (`web/`)

- **Formatter:** Prettier defaults via the editor.
- **Linter:** `tsc --noEmit` with `strict: true` (see `web/tsconfig.json`).
- **Naming:** `camelCase` for variables/functions, `PascalCase` for components and types, `UPPER_SNAKE_CASE` for constants.
- **Components:** function components only. Co-locate component, styles, and tests.
- **State:** TanStack Query for server state. `useState` / `useReducer` for local UI state. No Redux.

## Testing

- **Backend:** `pytest` in `api/tests/`. Use the existing `client` and `auth_headers` fixtures.
- **Frontend:** `vitest` in `web/tests/`. Component tests use `@testing-library/react`.
- **E2E:** Playwright in `web/e2e/`. The current smoke spec is **broken** (asserts English text on a Spanish UI) — see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

Aim to add tests for any user-facing change. A bug fix without a regression test will be sent back.

## Pre-commit hooks

```bash
pip install pre-commit
pre-commit install
```

Hooks run `ruff`, `mypy`, `tsc`, and `vitest` on the changed files. CI runs the same checks on every PR.

## Review process

- All PRs require **at least one approving review** before merge.
- Reviewers will check for: correctness, security implications, tests, documentation.
- Address review comments by pushing new commits (do not force-push mid-review).
- Once approved, the maintainer squashes and merges.

## Project structure (where to put things)

| You are adding…              | Put it in…                                              |
|------------------------------|---------------------------------------------------------|
| New API endpoint             | `api/app/api/v1/<resource>.py`                          |
| Business logic for a feature | `api/app/services/<resource>_service.py`                |
| Database model               | `api/app/models/<resource>.py` + new Alembic migration  |
| Pydantic schema              | `api/app/schemas/<resource>.py`                         |
| Background task              | `api/app/tasks/<resource>.py`                           |
| New page in the web app      | `web/app/<route>/page.tsx`                              |
| New component                | `web/components/<area>/<component>.tsx`                 |
| New hook                     | `web/hooks/use-<resource>.ts(x)`                        |
| Prompt template              | `_dev/prompts/<name>.md`                                |
| Architecture decision        | `docs/adr/<NNN>-<short-title>.md`                       |

## Reporting bugs

Use the [bug report issue template](.github/ISSUE_TEMPLATE/bug_report.yml). For security issues, follow [SECURITY.md](SECURITY.md) instead.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
