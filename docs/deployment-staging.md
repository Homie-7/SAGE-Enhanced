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
   | `SAGE_ADMIN_MODE` | `0` *(safe default — see Part D for when/why to flip this to `1` temporarily)* |
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
2. Create a project and step through Upload → Setup → Plan. **This alone
   already tests VAL for real** — every new project uses the configured
   default provider (`val`) whether or not admin mode is on. If planning
   completes, VAL is correctly wired; if it fails, the error message names
   exactly what's missing (bad URL, wrong style, rejected credential).
3. *(Optional, only if you want the quick diagnostic page instead of
   running a full project):* temporarily set `SAGE_ADMIN_MODE=1` in
   Railway's Variables tab, wait for the redeploy, then visit
   `https://<your-railway-domain>/api/admin/status` in a browser. You're
   looking for `"val": {"ready": true, ...}`. **When you're done checking,
   set `SAGE_ADMIN_MODE` back to `0`** in the same Variables tab (this is
   the only thing that variable controls — it does not affect which
   provider real projects use, only whether this diagnostic page and
   manual provider-switching are exposed).
4. Run one real project fully end-to-end (through rebuild/download) to
   confirm VAL completes a real task, not just that it reports "ready".

## Notes, assumptions, and known limits

- **`SAGE_ADMIN_MODE` should default to `0` on staging**, matching
  production exactly. It is *not* required to test VAL — every project
  already runs on VAL (the configured default) regardless of this
  setting. Flip it to `1` only for the brief window you want the
  `/api/admin/status` diagnostic page or manual provider-switching, then
  flip it back to `0`. Nothing about a normal user's experience changes
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
