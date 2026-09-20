# NahaVideo Launch Runbook

## What is implemented

- AI Director creative planning, shot scoring and semantic intelligence.
- Transcript, speech-safe pacing and music-beat intelligence.
- Caption hierarchy, rhythm and restrained motion.
- Per-shot intelligent reframing and multi-format variants.
- Stock/B-roll gap detection, provenance and approval.
- Self-hosted Cobalt import adapter with authorization gate.
- Final QA and auditable delivery manifest.
- Explainable Director rationale.
- Persistent project save/resume.
- Upload size limits and request rate limiting.
- Public-only URL validation for website intake, asset scouting and Cobalt source URLs.
- Security response headers and request IDs.
- Readiness endpoint at /api/ready.
- Privacy and Terms pages.
- Code-built shared SVG logo/favicon.
- Cinematic interactive landing page and separate production editor.
- Render production blueprint with persistent storage.

## Production Render configuration

Use the root render.yaml as the production configuration.

Render documents that persistent disks are available on paid services and preserve filesystem changes across deploys/restarts. The blueprint therefore uses a paid Starter service with a 10 GB disk mounted at /var/data.

## Final operator checklist

1. In Render, sync/apply render.yaml to the existing NahaVideo service.
2. Confirm the service is using the paid Starter profile and the nahavideo-data disk.
3. Confirm the health check path is /api/ready.
4. Keep automatic deployment set to CI checks passing.
5. Add optional NahaLLM, Jev and Cobalt environment variables only when those services are ready.
6. Open the public URL.
7. Verify /api/health returns the expected version and integration states.
8. Verify /api/ready returns ready: true.
9. Open the landing page and verify the animated hero.
10. Click Open Editor.
11. Upload 2–4 short clips.
12. Build a plan.
13. Save the project.
14. Refresh/restart the page and load the saved project.
15. Render a base MP4.
16. Render a platform pack.
17. Render 9:16 + 1:1 + 16:9 variants.
18. Open the downloaded outputs and verify audio, captions, framing and the branded close.
19. Run Final QA and build the Delivery Manifest before a client delivery.
20. Test Privacy and Terms links.

## Recommended first launch

Start with controlled client/prospect demos before opening unrestricted public usage.

Keep optional heavy local models disabled on the first production service unless compute capacity is sufficient.
