# SAGE staging deployment (Railway, single service)

The simplest way to get SAGE online: **one Railway service** hosts both the
API and the app itself (the backend serves the built frontend from the same
address). One login, one dashboard, one URL. No Vercel account, no CORS
setup, no copying URLs between two places.

## Steps

1. Go to [railway.app](https://railway.app), sign in, **New Project →
   Deploy from GitHub repo**, select `Homie-7/SAGE-Enhanced` and this
   branch. Railway reads `railway.json` and builds automatically — nothing
   else to configure here.
2. **Add a volume**: service → **Settings → Volumes → New Volume**, mount
   path `/data`. (Keeps uploaded projects and rebuilds across restarts.)
3. **Set environment variables**: service → **Variables** tab:

   | Variable | Value |
   |---|---|
   | `SAGE_PROVIDER` | `val` |
   | `SAGE_ADMIN_MODE` | `0` |
   | `SAGE_DB_PATH` | `/data/sage.db` |
   | `SAGE_ARTEFACT_ROOT` | `/data/artefacts` |
   | `VAL_API_KEY` | *your real VAL key — paste only here* |
   | `VAL_BASE_URL` | *your VAL gateway's base URL* |
   | `VAL_API_STYLE` | *`openai_chat` or `anthropic_messages`* |
   | `VAL_MODEL` | *the VAL model id* |

4. **Generate a public domain**: service → **Settings → Networking →
   Generate Domain**. Open it in a browser — that's the whole app.
5. Verify: the SAGE projects page should load. Step through Upload → Setup
   → Plan on one test project — this exercises VAL for real. If it fails,
   the error names exactly what's missing among the `VAL_*` variables.

That's it — 5 steps, one platform, no second deployment to wire up.

## If VAL readiness needs checking without running a project

Temporarily set `SAGE_ADMIN_MODE=1` in the same Variables tab, wait for the
redeploy, visit `https://<your-domain>/api/admin/status`. Set it back to
`0` afterwards — it only controls this diagnostic page and manual
provider-switching, never which provider real projects use.

## Notes / assumptions

- I don't know VAL's exact gateway shape — `VAL_BASE_URL`/`VAL_API_STYLE`/
  `VAL_MODEL` are placeholders for you to fill in from your VAL access
  details. Failures report exactly what's wrong (bad URL, wrong style,
  rejected credential).
- This is staging, not production: no custom domain, no autoscaling
  tuning. Fine for internal review with colleagues.
- A split Railway (API) + Vercel (frontend) path also exists in this repo
  (`frontend/vercel.json`, `frontend/.env.example`, `SAGE_CORS_ORIGINS`) in
  case you ever want the frontend on a separate platform — not needed for
  this default single-service path, and safe to ignore.
