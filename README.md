# ACOS — Autonomous Company Operating System

[![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/ci.yml)

ACOS is an agentic operations platform for small and medium-sized businesses. Six specialist
agents (HR, Finance, Inventory, Sales, Compliance and an Orchestrator) work over the company's
live data using **LLM tool-use** (provider-agnostic: Gemini, Anthropic, OpenAI, Groq or a local model), a **statistical/ML anomaly detector**, **retrieval over uploaded
documents**, and **persistent memory** — while every irreversible action is routed through a
**human-in-the-loop approval queue** protected by RBAC and OTP step-up.

> Problem: SMEs cannot afford dedicated analysts to catch invoice fraud, contract risk or stock-outs.
> ACOS performs the first-pass triage automatically and escalates only high-impact decisions to a human.

---

## Architecture

```
frontend/                      React 19 + Tailwind + shadcn/ui (Create React App / CRACO)
├── src/pages/Agents.jsx       Chat workspace: pick an agent like a model, converse, inspect tool traces
├── src/components/            AnomalyPanel, GoogleSignInButton, uploaders, dialogs …
├── api/index.py               Vercel Python serverless entrypoint  (→ server/app.py)
└── server/                    FastAPI application (single source of truth)
    ├── app.py                 app factory, CORS policy, lifespan (indexes, idempotent seed, scheduler)
    ├── core/                  config · db (Motor + GridFS) · security (JWT, RBAC, step-up) · guardrails · mailer
    ├── routers/               auth · users · records (CRUD/trash/history/CSV) · approvals · agents/chat · files · insights · admin
    ├── agents/                prompts · tools (28 typed tools, RBAC-checked) · runner (OpenAI-compatible tool-use loop)
    ├── ml/                    anomaly.py (Isolation Forest + Benford + robust z) · evaluate.py (precision/recall harness)
    ├── rag/                   ingest.py (PDF/TXT/CSV → chunks) · retrieve.py (BM25 over chunks & memory)
    ├── scheduler.py           background agent runs (in-process, or cron-triggered on serverless)
    └── tests/                 pytest suite (unit + API, runs in CI against MongoDB)
backend/server.py              thin local-dev shim so `uvicorn server:app` serves frontend/server
```

### How an agent run works

1. The user picks an agent and sends a message. The text is **normalised and risk-scored**
   (`core/guardrails.py`) — nothing is silently rewritten; the score is stored and audited.
2. `agents/runner.py` calls the configured LLM (any OpenAI-compatible endpoint — default Google Gemini) with the agent's **tool schema**. The model decides which tools
   to call (`run_anomaly_scan`, `search_contract_text`, `compute_reorder_plan`, `recall`, …).
3. Each tool is executed server-side **under the calling user's role**. State-changing, high-impact
   tools (`propose_payment`, `create_purchase_request`, terminations, big lead wins, high-risk
   contract changes) never mutate data — they create an **approval** for a human.
4. The model ends by calling `report_outcome` (structured confidence + review flag + next action);
   no text-template parsing.
5. The full **tool trace**, verdict and token usage are persisted with the conversation and shown
   in the UI. Approved actions are applied by `routers/approvals.py`, and every step is audit-logged.

### "ML detects → LLM explains → human approves"

`ml/anomaly.py` scores invoices with an **Isolation Forest** over engineered features (amount,
log-amount, per-vendor robust z-score, vendor frequency, round-amount, threshold-proximity,
duplicate count), a **Benford's-law χ² test**, and rule-based reasons. The Finance agent is
instructed to run this model before making claims and to explain its output in plain language.
`ml/evaluate.py` generates a labelled synthetic dataset (duplicates, structuring just below
approval thresholds, outliers, round amounts, new-vendor spikes) and reports precision / recall /
F1 — run `python -m ml.evaluate` or `GET /api/ml/evaluate`.

---

## Local development

```bash
# backend
cp backend/.env.example backend/.env       # fill MONGO_URL, JWT_SECRET, LLM_API_KEY, GOOGLE_CLIENT_ID
pip install -r backend/requirements.txt
cd backend && uvicorn server:app --reload --port 8001

# frontend
cp frontend/.env.example frontend/.env     # REACT_APP_BACKEND_URL=http://localhost:8001, REACT_APP_GOOGLE_CLIENT_ID
cd frontend && yarn install && yarn start
```

First start seeds demo records and four users with **random passwords printed once in the backend
log**. Alternatively set `BOOTSTRAP_ADMIN_EMAIL/PASSWORD` to create your own admin.

### Tests

```bash
pytest -c backend/pytest.ini -q          # unit + API tests (needs a local MongoDB)
cd frontend/server && python -m ml.evaluate
```

---

## Security model

| Control | Implementation |
|---|---|
| Authentication | bcrypt passwords (min 8 chars), 7-day JWT, Google Identity Services ID-token verified server-side with `google-auth` |
| Authorisation | Four roles (admin / manager / employee / auditor) enforced in every router **and** inside every agent tool |
| Step-up | Admin approval decisions require a 15-minute OTP-derived token (`X-OTP-Token`) |
| Prompt injection | Unicode normalisation, weighted risk scoring, structural separation of instructions/data, and capability control — the model can only *propose* side effects |
| CORS | Explicit origin allow-list with credentials; wildcard mode disables credentials (spec-compliant) |
| OTP hygiene | Codes are never returned by the API unless `DEBUG_OTP=true` **and** `APP_ENV != production` |
| Files | GridFS on MongoDB (async), type/size limits, text indexed for retrieval |
| Audit | Every login, CRUD, agent run, tool side effect, approval and suspected injection is written to `audit_logs` |

See [`docs/SECURITY_HARDENING.md`](docs/SECURITY_HARDENING.md) for the before/after write-up.

## Switching the LLM provider

| Provider | `LLM_BASE_URL` | `LLM_MODEL` example |
|---|---|---|
| Google Gemini (default, free tier) | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-flash-latest` |
| Anthropic | `https://api.anthropic.com/v1/` | `claude-sonnet-4-6` (+ `LLM_EXTRA_HEADERS={"anthropic-workspace-id":"wrkspc_…"}` if the key is org-scoped) |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| OpenAI | *(empty)* | `gpt-4.1-mini` |
| Ollama (local) | `http://localhost:11434/v1` | `qwen2.5:14b` |

`LLM_FALLBACK_MODEL` is tried automatically on rate-limit / capacity errors.

## Deployment

See [`DEPLOYMENT.md`](DEPLOYMENT.md) — Vercel (frontend + Python function in one project) with
MongoDB Atlas, Vercel Cron for scheduled agent runs, and the full environment-variable list.

## Licence

MIT
