# Security hardening — before / after

This document records vulnerabilities found during the internal review of the first prototype
and how each one was fixed. It is intended as evidence of engineering process, not as a list of
open issues.

| # | Finding (before) | Risk | Fix (after) | Where |
|---|---|---|---|---|
| 1 | Live-looking API keys pasted as "example values" in `DEPLOYMENT.md`; repo public | Credential leak / billing abuse | Keys rotated at the providers, history rewritten, docs now contain placeholders only; `.env*` git-ignored; `.env.example` files hold empty templates | `DEPLOYMENT.md`, `.gitignore`, `*/.env.example` |
| 2 | `DEBUG_OTP` defaulted to **true**, so `/auth/otp/request` and e-mail-verification resend returned the code in JSON whenever the e-mail provider was not configured | Account takeover if `RESEND_API_KEY` missing in prod | `DEBUG_OTP` defaults to **false** and is force-disabled when `APP_ENV=production`; password-reset never echoes the token | `core/config.py`, `routers/auth.py` |
| 3 | Prompt-injection "sanitizer" was a 6-pattern regex blocklist that rewrote user text (and false-positived on "you are … ai") | Trivial bypass; silent corruption of legitimate input | Defence in depth: NFKC normalisation + zero-width stripping, weighted **risk scoring** (logged & audited, never silently rewritten), structural separation (user text only in `user` turns, data only via tool results, system prompt marks both untrusted), and **capability control** — every tool checks the human caller's RBAC role and high-impact tools only create approval requests | `core/guardrails.py`, `agents/tools.py`, `agents/prompts.py` |
| 4 | `allow_origins=["*"]` together with `allow_credentials=True` | Invalid per CORS spec; browsers reject or, if worked around, wide open | Explicit origin allow-list from `CORS_ORIGINS`; wildcard mode automatically disables credentials | `app.py::build_cors_kwargs` |
| 5 | Blocking `requests.*` calls to a third-party object store inside async routes | Event-loop stalls under concurrent uploads | Storage moved to **MongoDB GridFS via Motor** (fully async); Google token verification and Resend calls wrapped in `asyncio.to_thread` | `core/storage.py`, `routers/auth.py`, `core/mailer.py` |
| 6 | Single 1 900-line `app.py` | Unreviewable; no unit boundaries | Split into `core/`, `routers/`, `agents/`, `ml/`, `rag/` packages with dependency injection via FastAPI `Depends` | `frontend/server/` |
| 7 | No CI; empty test artefacts committed | Regressions invisible | GitHub Actions runs the pytest suite (unit + API against MongoDB) and the frontend build on every push | `.github/workflows/ci.yml`, `frontend/server/tests/` |
| 8 | Default credentials (`admin@acos.io / admin123`) present in committed test reports | Trivial login on any deployment | Seed creates users with **random** passwords printed once to the server log; committed reports removed; first admin created from `BOOTSTRAP_ADMIN_*` env only | `seed.py` |
| 9 | Seed could double-insert schedules / agents on restart | Duplicate documents, UI glitches | Agents and schedules are **upserted by key** (`$setOnInsert`); unique indexes on `agents.key`, `schedules.agent_key`, `users.email` | `seed.py`, `core/db.py` |
| 10 | Login depended on a third-party auth gateway (two external hosts) | Vendor lock-in and availability dependency | Google Identity Services on the client; ID token verified server-side with `google-auth` against our own `GOOGLE_CLIENT_ID` | `components/GoogleSignInButton.jsx`, `routers/auth.py::google_login` |
| 11 | Passwords accepted at 6 characters | Weak credentials | Minimum 8 characters enforced on register, reset and change | `routers/auth.py` |
| 12 | Approvals could be decided twice; agent proposals had no executable payload | Inconsistent state | `409` on already-decided approvals; agent proposals carry a typed `proposed_action` that is applied **only after** human approval | `routers/approvals.py` |

## Residual risks / future work

* BM25 retrieval is lexical; a dense-embedding index (e.g. Voyage or a local model) would improve recall on paraphrased clauses.
* The Isolation Forest is unsupervised; with real labelled data a supervised model (gradient boosting) could be evaluated against it using the same harness.
* Rate limiting is applied to OTP requests only; a global per-IP limiter at the edge (Vercel WAF / Cloudflare) is recommended.
* Tool-result size is capped at 12 kB per call; very large documents should be summarised in a pre-processing step.
