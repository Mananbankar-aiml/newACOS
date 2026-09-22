# ACOS — Autonomous Company Operating System

## Original Problem Statement
Import all content from https://github.com/bankarmanan8-boop/ACOS, build/extend features on top of it, wire in Resend for real emails, promote `bankarmanan8@gmail.com` to admin, and restructure the codebase so it can deploy to Vercel with a valid `vercel.json`.

## Architecture
- **Backend:** FastAPI + MongoDB (motor) — `backend/server.py`
- **LLM:** Claude Sonnet 4.6 via `emergentintegrations` (Emergent Universal Key)
- **Auth:** JWT + bcrypt · 4 roles (admin / manager / employee / auditor) · Emergent Google SSO
- **Frontend:** React 19 (JSX) · TailwindCSS · react-router-dom v7 · axios (relative `/api` fallback)
- **Motion:** GSAP + react-fast-marquee (cinematic footer)
- **Charts:** recharts (Analytics)
- **Email:** Resend (live — key configured)
- **Deployment:** Vercel serverless (`api/index.py` wraps FastAPI ASGI app) + static CRA build

## User Personas
- **Manan Bankar (bootstrap admin, real account)** — full access
- **Ava Reyes / Marcus Nolan / Elena Park / Kenji Ito** — demo admin/manager/employee/auditor

## What's Been Implemented (Jul 2026 — current session)
### Existing (imported from GitHub repo)
- JWT + email OTP + forgot-reset password + Emergent Google SSO
- 6-agent LLM runner (orchestrator/hr/finance/inventory/sales/compliance)
- Human-in-the-loop approvals, immutable audit log
- 11 pages: Dashboard, Agents, HR, Finance, Inventory, Sales, Compliance, Analytics, Approvals, Audit Logs, Settings
- File uploads (Emergent object storage), CSV import
- RBAC filtering on read paths, employee scoping
- Configurable per-agent scheduled runs (in-process asyncio poller)
- Prompt-injection sanitizer, emails log viewer

### Added this session (Jul 11 2026): real emails now sent (verified via forgot-password flow → `provider=resend, status=sent`)
- **Demo data seed** — `POST /api/admin/seed-demo` inserts 30 employees + 50 invoices + 80 inventory + 25 leads + 8 contracts marked with `seeded: true`; `POST /api/admin/wipe-demo` removes them cleanly (leaves real data alone). Seed/Wipe buttons on Settings for admins.
- **CSV export** — `GET /api/export/{collection}` streams CSV for 6 modules. Export button next to Import on every page. Admin + manager only; audited.
- **Audit log RBAC** — `/api/audit-logs` restricted to admin + manager (was any authenticated user). Audit nav item auto-hidden for employee and auditor via `adminManagerOnly` flag in `gradient-menu.jsx`.
- **Bootstrap admin**: idempotent `bootstrap_admin()` promotes/creates `bankarmanan8@gmail.com` as admin on every startup and refreshes password to `BOOTSTRAP_ADMIN_PASSWORD`; keeps Google auth working too.
- **Serverless-safe backend**: scheduler loop is auto-disabled when `VERCEL=1` env var is set (Vercel runtime).
- **Single-folder Vercel deploy** (free-tier compatible):
  - `frontend/` is the single Vercel Root Directory
  - `frontend/api/index.py` — Python serverless entrypoint (Vercel auto-detects)
  - `frontend/server/app.py` — canonical FastAPI code (moved from `backend/server.py`)
  - `frontend/api/requirements.txt` — Python deps for the function
  - `frontend/vercel.json` — rewrites `/api/*` → serverless function
  - `backend/server.py` — 3-line shim so local supervisor preview still runs
  - `DEPLOYMENT.md` — updated walkthrough for the single-folder pattern
- **Frontend same-origin API**: `frontend/src/lib/api.js` now falls back to relative `/api` when `REACT_APP_BACKEND_URL` is empty — required for the single-folder Vercel deploy.

## Prioritized Backlog
### P1 (next options offered to user)
- Vector RAG over uploaded contracts (FAISS)
- Real ML-driven anomaly detection dashboard
- Real-time notifications via websockets
- Slack integration for approvals / escalations
- Global AI chat command-bar

### P2
- Vercel Cron endpoint to replace in-process scheduler
- Direct-to-S3 upload for large PDFs (bypass Vercel 4.5 MB limit)
- SSO for Microsoft 365
- SMS/WhatsApp via Twilio for approval notifications

### P3
- Genetic-algorithm shift scheduler (DEAP) for HR agent
- Cost telemetry per agent run

## Test Credentials
See `/app/memory/test_credentials.md`.

## Deployment
See `/app/DEPLOYMENT.md`.
