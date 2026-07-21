# SAGE staging deployment — alternative path (Railway, single service)

> **This is no longer the recommended path.** Staging now defaults to
> Google Cloud Run — see `docs/deployment-cloud-run.md`. This guide is kept
> for anyone who later prefers Railway instead; the same root `Dockerfile`
> works on both unchanged.

The simplest way to get SAGE online: **one Railway service** hosts both the
API and the app itself (the backend serves the built frontend from the same
address). One login, one dashboard, one URL. No CORS setup, no copying
URLs between two places, no separate frontend platform.

## Steps

1. Go to [railway.app](https://railway.app), sign in, **New Project →
   Deploy from GitHub repo**, select `Homie-7/SAGE-Enhanced` and this
   branch. Railway auto-detects the root `Dockerfile` and builds it —
   nothing else to configure here.
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

   (`VAL_BASE_URL`/`VAL_API_STYLE`/`VAL_MODEL` no longer need setting here —
   `prompts/configs/val.json` now ships wired to the real RMIT gateway. Only
   add these as variables if you want to point this specific deployment at
   a different gateway/model than what's checked in.)

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

- VAL is wired to the real RMIT NPE gateway (`prompts/configs/val.json`) —
  only `VAL_API_KEY` (the secret) needs supplying. Failures report exactly
  what's wrong (bad URL, wrong style, rejected credential) if that ever
  changes.
- This is staging, not production: no custom domain, no autoscaling
  tuning. Fine for internal review with colleagues.
