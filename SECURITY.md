# Security Policy

## Supported versions

| Version | Supported          |
|---------|--------------------|
| `main`  | :white_check_mark: |
| older   | :x:                |

Only the `main` branch receives security updates. Stacked branches (`stack-1-scaffold` through `stack-5-frontend`) are historical and will not receive patches.

## Reporting a vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Email security reports to the maintainers (see the commit history for contact). A response is expected within 72 hours. Include:

- A clear description of the issue and its impact.
- Steps to reproduce, ideally with a minimal PoC.
- The affected commit SHA and branch.

We follow responsible disclosure. We will not take legal action against researchers who follow this policy.

## Hardening checklist for production deployments

Before exposing VigilaGraph to the public internet, ensure the following:

### Required (CRITICAL — the app will be insecure without these)

- [ ] **`JWT_SECRET`** is a randomly-generated string of at least 32 bytes (`openssl rand -hex 32`). The default `CHANGE-ME` is rejected at startup.
- [ ] **`S3_ACCESS_KEY` / `S3_SECRET_KEY`** are set to real values (or storage is switched to local filesystem via `STORAGE_LOCAL_PATH`).
- [ ] **HTTPS** is terminated at the load balancer or reverse proxy. HSTS headers are enabled.
- [ ] **`ENV=production`** is set. The dev-only `seed-test-docs` endpoint is disabled in production builds.

### Strongly recommended (HIGH)

- [ ] Rate limiting on `/auth/login` and `/auth/register` (5/min per IP+email).
- [ ] Migrate JWT storage from `localStorage` to `httpOnly Secure SameSite` cookies.
- [ ] Security headers (`Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security`).
- [ ] PII redaction in log output.
- [ ] Audit log table for sensitive operations (login, password change, project create/delete).
- [ ] Database backups configured (managed by Railway/Render, or manual `pg_dump` cron).
- [ ] Error tracking (Sentry or equivalent) wired up.

### Recommended (MEDIUM)

- [ ] Dependency vulnerability scanning in CI (`pip-audit` for Python, `bun audit` or `npm audit` for JS).
- [ ] Dependabot enabled for automated PR creation on dependency updates.
- [ ] Branch protection on `main`: require PR + 1 review + CI green.
- [ ] Required status checks on `main` before merge.

## Known security advisories (current codebase)

The following issues are **known and unfixed** at the time of writing. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full audit:

1. Default `JWT_SECRET` value is publicly known (mitigated by required-env check, see checklist above).
2. JWT tokens stored in `localStorage` on the web client.
3. No rate limit on login endpoint.
4. No security headers middleware.
5. E2E test suite references English copy that no longer exists — CI may be red.
6. Pre-commit hook paths reference `apps/` instead of the current `api/` / `web/` paths.

## Disclosure timeline

We aim for:

- **72h** initial response.
- **30 days** coordinated disclosure window (extendable for complex issues).
- **Public advisory** released once a fix is shipped, or after the 30-day window.
