# NahaVideo AI Director — v0.3 Build Plan

## Goal
Turn the local-first editor into an explainable AI Director that can combine deterministic media signals with optional local model intelligence.

## v0.3 shipped
- Optional local faster-whisper transcription adapter with word timestamps.
- Optional local OpenCLIP semantic vision adapter.
- Director scoring now combines visual quality, food/hero semantic relevance, filename priors and speech signals.
- Transcript-aware shot-window selection for dialogue-led edits.
- Transcript-to-output duck ranges for deterministic music lowering during speech.
- Editable timeline: reorder, trim and remove/restore decisions before rendering.
- Plan sanitisation before render so disabled or unknown clips are ignored safely.
- Optional NahaLabs logo upload and logo-card overlay.
- Versioned edit decision graph explaining the main creative rules.
- Lightweight base requirements remain CPU-friendly; model dependencies are isolated in requirements-models.txt.

## Model switches
The base editor runs without model downloads.

Enable Whisper:
`NAHAVIDEO_ENABLE_TRANSCRIBE=1`
Optional model:
`NAHAVIDEO_WHISPER_MODEL=tiny`

Enable OpenCLIP:
`NAHAVIDEO_ENABLE_VISION=1`
Optional model:
`NAHAVIDEO_CLIP_MODEL=ViT-B-32`
`NAHAVIDEO_CLIP_PRETRAINED=openai`

## Explicit limitations
- OpenCLIP and Whisper are optional and can be heavy on CPU/RAM.
- Semantic analysis is generic zero-shot labelling, not a custom NahaLabs-trained restaurant model.
- Logo animation is currently FFmpeg overlay; the proprietary NahaLabs motion-graphics engine can become the branding layer later.
- Dialogue ducking is transcript-range based when Whisper is available, with sidechain fallback otherwise.
