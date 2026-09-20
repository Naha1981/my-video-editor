# NahaLabs Jev Browser Worker

Separate browser execution service for NahaVideo.

It is intentionally not imported by the NahaVideo renderer. NahaVideo calls this service through `JEV_WORKER_URL`.

## Environment

- `JEV_WORKER_API_KEY`
- `JEV_ALLOWED_DOMAINS` — comma-separated optional production allowlist
- `JEV_MISSION_TIMEOUT_SECONDS` — default 180
- `JEV_MAX_STEPS` — default 40
- `TYPESAFE_API_KEY` — Jev's action-policy credential
- `TEXT_MODEL_API_KEY` — field-value helper credential
- `TEXT_MODEL_BASE_URL` — can point to NahaLLM `/v1`
- `TEXT_MODEL` — can be `fast`
- `TEXT_MODEL_REASONING` — optional provider setting

For a NahaLLM-backed field helper:

`TEXT_MODEL_BASE_URL=https://<nahallm-service>/v1`

`TEXT_MODEL=fast`

`TEXT_MODEL_API_KEY=<the NahaLLM app key>`

Jev's current operation/target policy remains its TypeSafe interface; NahaLLM is the shared text/interpretation layer around it.

## Security

The worker blocks private/local/link-local/reserved target addresses, supports a domain allowlist, enforces an API key, caps steps/time, and only executes the Jev library's supported browser operations.

The worker's asset extraction is fixed code-owned JavaScript after the browser task; model output is never executed as JavaScript or shell commands.
