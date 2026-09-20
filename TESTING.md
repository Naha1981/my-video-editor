# NahaVideo v0.20 — First Smoke Test

## What this test proves

Run the local app through the real browser flow:

1. Upload 2–4 short video clips.
2. Give the Director a natural-language brief.
3. Compile the NahaLabs creative command context.
4. Build the story sequence and footage-gap report.
5. Render one MP4.
6. Inspect the output and delivery QA.
7. Optionally render a multi-platform pack when ffmpeg-skill is installed.

## Windows quick start

Use PowerShell in the repository folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\start_windows.ps1
```

The launcher creates a local `.venv`, installs the base requirements, checks for FFmpeg and starts FastAPI on:

`http://127.0.0.1:8000`

Open that address in Chrome.

## First test input

Use 2–4 real clips, ideally 3–15 seconds each. Keep the first test lightweight.

Recommended brief:

> Create a 15-second premium South African restaurant advertisement. Start with the strongest food shot, remove dead time, keep the pacing energetic, show the experience, and finish with the NahaLabs logo.

Recommended command:

`/lead-gen /reel /nahalabs-authentic`

For the first smoke test, leave Whisper and OpenCLIP disabled.

## Pass criteria

The browser should let you:

- upload footage without an error
- generate a Director plan
- see an ordered AI story sequence
- see any missing footage as an explicit gap
- edit the timeline before rendering
- render an MP4
- download/play the MP4
- see delivery QA status

A successful base render is the minimum passing result. FFmpeg Skill platform rendering is an additional test and is only exercised when that skill is installed.

## Second test

After the base render passes:

1. Upload one approved stock/B-roll clip.
2. Enter its provider, source URL, licence and attribution.
3. Attach the matching creative intent.
4. Rebuild the plan.
5. Confirm the stock clip can fill the relevant gap.
6. Confirm the provenance metadata is retained.

## Performance note

NahaVideo's base path is CPU-friendly. Do not enable local Whisper or OpenCLIP on the first test on a low-RAM machine; add those only after the deterministic path is working.
