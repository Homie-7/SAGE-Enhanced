# SAGE staging deployment (Railway + Vercel)

This is a step-by-step guide for putting SAGE on the web so you can use it
in a browser and share the link with colleagues. It assumes no prior
Railway/Vercel experience. It does **not** cover production hardening —
this is a staging deployment for internal review.

Two separate services:
- **Backend** (the API + engine) → **Railway**
- **Frontend** (what you see in the browser) → **Vercel**

They talk to each other over the public internet, so each needs to know
the other's web address. You'll copy two URLs between the two dashboards
during setup — that's the only fiddly part, and it's spelled out below.

---

## Part A — Deploy the backend on Railway

1. Go to [railway.app](https://railway.app), sign in, click **New Project →
   Deploy from GitHub repo**, and select `Homie-7/SAGE-Enhanced`.
2. Railway will read this repo's `railway.json` and build automatically —
   you do not need to set a root directory or build command.
3. **Add a volume** (so uploaded projects and rebuilt files survive
   restarts): in the service → **Settings → Volumes → New Volume**, mount
   path `/data`.
4. **Set environment variables**: service → **Variables** tab, add each of
   these (values in *italics* are yours to fill in):

   | Variable | Value |
   |---|---|
   | `SAGE_PROVIDER` | `val` |
   | `SAGE_ADMIN_MODE` | `1` *(shows the admin status page for staging; see Part D)* |
   | `SAGE_DB_PATH` | `/data/sage.db` |
   | `SAGE_ARTEFACT_ROOT` | `/data/artefacts` |
   | `VAL_API_KEY` | *your real VAL key — paste it only here, nowhere else* |
   | `VAL_BASE_URL` | *your VAL gateway's base URL* |
   | `VAL_API_STYLE` | *`openai_chat` or `anthropic_messages` — whichever your VAL gateway speaks* |
   | `VAL_MODEL` | *the VAL model id you want SAGE to use, e.g. one of the Opus/GPT ids VAL exposes* |
   | `SAGE_CORS_ORIGINS` | leave blank for now — you'll fill this in during Part C |

5. **Generate a public domain**: service → **Settings → Networking →
   Generate Domain**. Copy this URL (it looks like
   `https://sage-enhanced-production.up.railway.app`) — you need it in
   Part B.
6. Wait for the deploy to go green, then visit
   `https://<that-domain>/api/health` in your browser. You should see
   `{"status":"ok",...}`. If so, the backend is live.

## Part B — Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com), sign in, click **Add New →
   Project**, and import `Homie-7/SAGE-Enhanced`.
2. When configuring the project: set **Root Directory** to `frontend`.
   Vercel will auto-detect the Vite framework preset — leave build/output
   settings as detected.
3. Before deploying, add one environment variable: **Settings →
   Environment Variables**:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://<your-railway-domain>/api` (from Part A step 5) |

4. Deploy. Vercel gives you a URL like
   `https://sage-enhanced.vercel.app` — copy it.

## Part C — Connect the two (CORS)

The backend only accepts browser requests from origins you explicitly
allow. Go back to Railway → your backend service → **Variables**, and set:

| Variable | Value |
|---|---|
| `SAGE_CORS_ORIGINS` | `https://<your-vercel-domain>` (from Part B step 4) |

Railway will redeploy automatically. That's the last connection step.

## Part D — Verify it's working

1. Open your Vercel URL in a browser. You should see the SAGE projects
   page (not a blank screen or an error).
2. Create a project and step through Upload → Setup — if these load and
   save without errors, the frontend is talking to the backend correctly.
3. **Check VAL is wired correctly** (admin/dev status page — only visible
   because `SAGE_ADMIN_MODE=1`): visit
   `https://<your-railway-domain>/api/admin/status` directly in a browser,
   or look for the provider status panel on the projects page in the app.
   You're looking for `"val": {"ready": true, ...}`. If it instead reports
   missing facts (e.g. `base_url`), double check the `VAL_*` variables in
   Part A step 4.
4. Run one real project end-to-end (upload a real XML + transcript,
   through to rebuild/download) to confirm VAL actually completes a task,
   not just that it's "ready" per config.

## Notes, assumptions, and known limits

- **`SAGE_ADMIN_MODE=1` for staging is intentional** — it's what lets you
  see provider status and test VAL from the browser without a technical
  admin doing it via API calls. This is exactly what "admin/dev deployment"
  means in SAGE's design — it does not violate the managed-service rule,
  since standard/production deployments would set this to `0`. If you'd
  rather staging behave exactly like production (no visible provider
  status), set it to `0` — the app will work identically for end users
  either way.
- **`VAL_API_STYLE` and `VAL_BASE_URL`**: I don't know VAL's exact gateway
  shape (whether it looks like OpenAI's or Anthropic's chat API). If the
  first live call fails, the error message returned by `/api/admin/status`
  or a failed planning run will say exactly what's wrong (wrong style,
  wrong URL, bad credential) — nothing here fails silently.
- **The "mock" provider** (used for zero-cost test fixtures) won't be
  selectable in this hosted image — its fixture files live in
  `backend/tests/`, which isn't shipped to keep the deployed image small.
  This doesn't affect VAL or standard usage; it only affects the
  fixture-driven dev/test path, which isn't relevant on staging.
- **This is staging, not production**: no custom domain, no autoscaling
  tuning, no rate limiting beyond what's already in the app. Fine for
  internal review with colleagues; revisit before any public or
  higher-stakes use.
