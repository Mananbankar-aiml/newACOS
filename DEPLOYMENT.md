# Deployment (Vercel + MongoDB Atlas)

Everything Vercel needs lives inside `frontend/` — that folder is the project's Root Directory.
The React app is served statically and `frontend/api/index.py` is deployed as a Python serverless
function that exposes the FastAPI app in `frontend/server/`. `frontend/vercel.json` rewrites `/api/*`
to that function.

## 1. Prerequisites

| Service | Why | Free tier |
|---|---|---|
| MongoDB Atlas | database **and** file storage (GridFS) | M0, 512 MB |
| Google AI Studio | Gemini API key for agent tool-use (any OpenAI-compatible provider works) | free tier |
| Google Cloud Console | OAuth 2.0 Client ID (Web) for "Sign in with Google" | free |
| Resend (optional) | real OTP / notification e-mails; without it e-mails are logged to the console | 3 000 / month |

Google Cloud Console → Credentials → OAuth 2.0 Client ID (Web application):
* Authorised JavaScript origins: `https://<your-app>.vercel.app` (plus `http://localhost:3000` for dev)
* No redirect URI is required — the app uses the Google Identity Services ID-token flow.

## 2. Vercel project

1. Import the GitHub repo → **Root Directory = `frontend`**, framework = Create React App.
2. Add the environment variables below.
3. Deploy.

### Environment variables

| Key | Value |
|---|---|
| `MONGO_URL` | Atlas connection string |
| `DB_NAME` | `acos` |
| `JWT_SECRET` | 32+ random bytes, e.g. `openssl rand -hex 32` |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | `https://<your-app>.vercel.app` (comma-separated if several) |
| `FRONTEND_URL` | `https://<your-app>.vercel.app` (used in password-reset e-mails) |
| `LLM_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/` (Gemini) — see README for other providers |
| `LLM_API_KEY` | provider API key |
| `LLM_MODEL` | `gemini-flash-latest` |
| `LLM_FALLBACK_MODEL` | `gemini-flash-lite-latest` |
| `LLM_EXTRA_HEADERS` | optional JSON of extra headers |
| `GOOGLE_CLIENT_ID` | `…apps.googleusercontent.com` |
| `REACT_APP_GOOGLE_CLIENT_ID` | same value (build-time, frontend) |
| `REACT_APP_BACKEND_URL` | leave **empty** → same-origin `/api` |
| `RESEND_API_KEY`, `SENDER_EMAIL` | optional |
| `DEBUG_OTP` | `false` |
| `CRON_SECRET` | random string; shared with Vercel Cron |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_NAME`, `BOOTSTRAP_ADMIN_PASSWORD` | first admin account (created only if it does not exist) |
| `MAX_UPLOAD_MB` | `4` (Vercel request-body limit is 4.5 MB) |

Never paste real values into documentation or commit `.env` files (`.gitignore` already excludes them).

## 3. Scheduled agent runs on serverless

The in-process scheduler is disabled when `VERCEL=1`. Add to `frontend/vercel.json`:

```json
"crons": [{ "path": "/api/internal/scheduler/tick", "schedule": "*/30 * * * *" }]
```

Vercel Cron does not send custom headers on the Hobby plan, so either use a Pro plan with
`X-Cron-Secret`, or trigger the tick from an external scheduler (GitHub Actions `schedule`,
cron-job.org) with `-H "X-Cron-Secret: $CRON_SECRET"`.

## 4. Post-deploy checklist

* `GET /api/health` → `{"status":"ok","llm_configured":true,"google_auth":true}`
* Sign in with Google → new users get role `pending`; an admin assigns roles in Settings → Team.
* Finance → **Run scan** shows the ML anomaly report; Agents → Finance Agent explains it.
* Approvals → admin decisions prompt for OTP (e-mailed via Resend, or console-logged).
