# NahaVideo on Render — Free Web Service

Use a normal **Web Service** for the first deployment. Do not use the Blueprint flow for this test.

## Render Dashboard

1. New → Web Service.
2. Connect GitHub repository: `Naha1981/my-video-editor`
3. Branch: `main`
4. Runtime: `Docker`
5. Plan: `Free`
6. Health Check Path: `/api/health`
7. Auto Deploy: `Yes`

The repository already contains the Dockerfile. Leave Build Command and Start Command at their Docker defaults.

## Environment variables

Set:

- `PYTHONUNBUFFERED=1`
- `NAHAVIDEO_ENABLE_TRANSCRIBE=0`
- `NAHAVIDEO_ENABLE_VISION=0`
- `NAHAVIDEO_ENABLE_AUDIO_INTELLIGENCE=0`
- `NAHAVIDEO_RENDER_PROFILE=render_free`

The Render Free profile uses a lower 720x1280 render size and a faster H.264 preset to reduce memory pressure.

## First cloud test

Open the deployed `onrender.com` URL.

Use:

`/lead-gen /reel /nahalabs-authentic`

Brief:

`Create a 15-second premium South African restaurant advertisement. Start with the strongest food shot, remove dead time, keep the pacing energetic, show the experience, and finish with the NahaLabs logo.`

Start with 2–4 short clips.

## Free-plan limitation

Render Free web services have an ephemeral filesystem. Uploaded footage and generated MP4s are therefore temporary and can disappear after a restart/spin-down. This deployment is for functional testing, not production media storage.

For production, move media to object storage and use a paid compute profile with more RAM.

## NahaLLM + Jev architecture

NahaVideo remains the existing video application. Two optional services sit beside it:

NahaVideo Web Service
→ NahaLLM Web Service
→ configured LLM providers

NahaVideo Web Service
→ Jev Browser Worker
→ Chromium / Browser Harness

Jev is not installed into the NahaVideo renderer.

### NahaVideo environment

- `NAHALLM_ENABLED=1`
- `NAHALLM_BASE_URL=https://<nahallm-service>.onrender.com`
- `NAHALLM_API_KEY=<per-app NahaLLM key>`
- `NAHALLM_TIMEOUT_SECONDS=45`
- `JEV_ENABLED=1`
- `JEV_WORKER_URL=https://<jev_worker-service>.onrender.com`
- `JEV_WORKER_API_KEY=<jev_worker-key>`
- `JEV_ALLOWED_DOMAINS=<approved domains, comma-separated>`
- `JEV_TIMEOUT_SECONDS=240`

### NahaLLM Web Service

Create a separate Render Web Service from `Naha1981/NahaLLM`.

Runtime: Docker.

Required provider secrets stay in NahaLLM only:

- `NAHALLM_API_KEYS`
- `GROQ_API_KEY` and/or other configured provider keys
- provider model configuration as required

The NahaVideo service receives only its application NahaLLM key.

### Automatic asset collection

For public media collection, configure the NahaVideo service with:

- `NAHAVIDEO_ASSET_MAX_BYTES=83886080`
- `NAHAVIDEO_ASSET_ALLOWED_DOMAINS=<approved CDN/provider domains, comma-separated>`

Only HTTP(S) media on the source domain or explicitly allowlisted domains can be collected. Private/local/reserved destinations are blocked. Downloaded stock video is always marked pending until provenance/license is approved.

To enable automatic stock searches when a Director gap exists, Jev must be enabled and the operator can use **Find missing stock/B-roll automatically** in the UI.

### Jev Browser Worker

Create another Render Web Service from this repository using:

- Runtime: Docker
- Dockerfile Path: `jev_worker/Dockerfile`
- Docker Build Context: repository root

Required:

- `JEV_WORKER_API_KEY`
- `TYPESAFE_API_KEY`

Optional:

- `JEV_ALLOWED_DOMAINS`
- `JEV_MISSION_TIMEOUT_SECONDS`
- `JEV_MAX_STEPS`
- `TEXT_MODEL_BASE_URL=https://<nahallm-service>.onrender.com/v1`
- `TEXT_MODEL=fast`
- `TEXT_MODEL_API_KEY=<NahaLLM app key>`

The Jev worker uses the NahaLabs fork's browser policy and Browser Harness. Its operation/target decision layer remains Jev's existing TypeSafe path; NahaLLM provides the shared text helper/interpretation layer around it.

### Resource note

The Jev worker runs Chromium and Browser Harness and should be treated as a separate browser runtime. Do not force it into the 512 MB NahaVideo Free renderer. Validate browser startup and memory on the chosen Render service before treating it as production infrastructure.


## Production profile

The root render.yaml now defines the production service: paid Starter compute, a 10 GB persistent disk at /var/data, HTTP readiness at /api/ready, 300-second graceful shutdown and CI-gated auto-deploys. Render documents persistent disks as the mechanism for preserving service filesystem changes across deploys/restarts, and HTTP health checks as application-level readiness checks. citeturn250335search1turn250335search3turn217056view0


## Optional operator authentication

Set `NAHAVIDEO_AUTH_PASSWORD` and `NAHAVIDEO_AUTH_SECRET` as Render secrets to turn on the editor/API operator sign-in gate. Leave them unset for the public demo mode. The secret is used only to sign short-lived session cookies; the password is never returned by the API.
