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
