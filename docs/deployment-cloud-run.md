# SAGE staging deployment (Google Cloud Run — recommended)

**One container, one Google Cloud service, one URL.** The existing root
`Dockerfile` already does everything Cloud Run needs (builds the frontend,
serves it + the API from one process, listens on `$PORT`) — nothing about
the image changes for this platform. This is simpler than the Railway path
for a Google-native setup, and simpler than Firebase App Hosting for this
repo specifically: App Hosting is built around detecting a JS framework
(Next.js/Angular) and its own build system: it doesn't have a first-class
"just build my Dockerfile" story, whereas Cloud Run's entire contract *is*
"give me a container." Since SAGE already has a working Dockerfile, Cloud
Run is the least-friction option, not a workaround.

## Steps

1. Go to [console.cloud.google.com/run](https://console.cloud.google.com/run)
   (create/select a Google Cloud project first if you don't have one — it
   will prompt you and ask you to enable billing, standard for any Cloud
   Run project).
2. **Create Service → Continuously deploy from a repository (source)** →
   **Set up with Cloud Build** → connect your GitHub account → select
   `Homie-7/SAGE-Enhanced`, branch `deploy/staging-vercel-railway`.
3. When asked for build type, choose **Dockerfile**, path `/Dockerfile`
   (repo root — already correct by default).
4. Region: pick whichever is closest to you/colleagues (e.g.
   `australia-southeast1`). Authentication: **Allow unauthenticated
   invocations** (so colleagues can open it in a browser without a Google
   login prompt — fine for internal staging review).
5. **Variables & Secrets** tab, add:

   | Variable | Value |
   |---|---|
   | `SAGE_PROVIDER` | `val` |
   | `SAGE_ADMIN_MODE` | `0` |

   (`VAL_BASE_URL`/`VAL_API_STYLE`/`VAL_MODEL` don't need setting —
   `prompts/configs/val.json` already ships wired to the real RMIT NPE
   gateway. Only add these as variables if you want this deployment to use
   a different gateway/model than what's checked in.)

   Then add `VAL_API_KEY` as a **secret**, not a plain variable: click
   **Reference a secret** → **Create new secret** → paste your real VAL
   key as the secret value → mount it as environment variable
   `VAL_API_KEY`. This is Cloud Run's built-in secret store (Secret
   Manager) — the key is encrypted at rest and never appears in the
   service's plain config, build logs, or the console's variable list.

   (`SAGE_DB_PATH` / `SAGE_ARTEFACT_ROOT` / `SAGE_PROMPTS_ROOT` /
   `SAGE_STATIC_ROOT` need no entry — the Dockerfile already sets sane
   defaults.)

6. Click **Create**. Cloud Build builds the image and deploys it; Cloud
   Run gives you a URL like `https://sage-enhanced-xxxxx.a.run.app`.
7. Open that URL. Step through Upload → Setup → Plan on one test project —
   this exercises VAL for real, not just a config check.

That's it — one platform, no volumes to attach, no second dashboard.

## If VAL readiness needs checking without running a project

Temporarily set `SAGE_ADMIN_MODE=1` in the Cloud Run service's **Edit &
Deploy New Revision → Variables** tab, deploy, visit
`https://<your-url>/api/admin/status`. Set it back to `0` and redeploy
afterwards — it only controls this diagnostic page and manual
provider-switching, never which provider real projects use.

## Important limitation: storage is ephemeral

Cloud Run containers have **no persistent disk by default**. SAGE's
SQLite database and uploaded/rebuilt files live at `/tmp` inside the
container (see Dockerfile), which is wiped whenever:
- the service scales to zero and a new instance starts,
- a new revision is deployed,
- Google recycles the instance for any platform reason.

For a short internal review session this is usually fine — but **don't
treat uploaded staging projects as durable**. If you want data to survive
restarts, the fix is adding real persistent storage (e.g. a mounted Cloud
Storage bucket, or moving off SQLite to Cloud SQL) — that's an
architecture change, out of scope here since it wasn't asked for and isn't
needed just to get staging online. Flagging it now so it's a deliberate
choice, not a surprise.

Optional mitigation with no code change: in the service's **Edit & Deploy
New Revision → Container → Autoscaling**, set **Minimum instances = 1**.
This avoids the *scale-to-zero* case (the most common way state gets
wiped between casual use) — it does not protect against redeploys or
Google-initiated instance recycling.

## Notes / assumptions

- VAL is wired to the real RMIT NPE gateway and confirmed working (a live
  round-trip has been run against it). Only `VAL_API_KEY` (the secret)
  needs supplying per deployment.
- This is staging, not production: no custom domain, no autoscaling
  tuning beyond the optional note above.
- The Railway path (`docs/deployment-staging.md`) still works unchanged
  if you ever want it instead — same Dockerfile, different platform.
