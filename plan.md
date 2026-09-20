# NahaVideo AI Director — v0.7 Build Plan

## Goal
Turn the local-first editor into an explainable AI Director that can combine deterministic media signals with optional local model intelligence.

## v0.7 shipped
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


## v0.7 shipped
- Local website URL intake extracts title, description and visible text using the Python standard library.
- Deterministic creative-brief compiler produces business category, offer, audience, tone, CTA and visual requirements.
- Stock-shot requirement generator turns the brief into a practical footage shopping list.
- Timeline rendering now preserves clip/logo order.
- Transcript captions can be burned into the rendered MP4 and are rebuilt after timeline edits.
- NahaLabs motion graphics now has an explicit adapter seam so the proprietary motion engine can replace the FFmpeg fallback.

### Website workflow
Client website URL → Brand intake → Creative brief → Shot requirements → Footage → AI Director → Storyboard → Captions → NahaLabs motion graphics → MP4

The website intake is intentionally deterministic and local-first. It does not claim to understand a site with an external LLM; the extracted brief remains editable and can later be connected to a local model.


## v0.7 — Creative Director
- Added a deterministic creative-direction engine that turns brand/brief context into an ad concept, hook, promise, proof path, CTA and shot sequence.
- Restaurant direction includes sensory hero, experience and signature concepts; general business direction includes outcome, problem→solution and proof concepts.
- The selected concept is attached to every edit plan and surfaced in the UI.
- Storyboard beats now carry explicit creative shot intent such as `hero_food`, `craft`, `proof`, `experience`, `result` and `cta`.
- Website intake now feeds the Creative Director before the editing plan is produced.


## v0.7 — Creative-to-Footage Matching
- The Director now uses the selected creative concept's shot sequence as an additional footage-ranking signal.
- Filename evidence can now match creative intents such as hero_food, experience, proof, result and cta.
- Stock-shot requirements identify hook and CTA footage as required, with supporting footage separated for procurement/planning.
- This is intentionally additive: visual quality, semantic relevance, speech and other existing signals remain part of ranking.


## v0.9 — AI Story Sequence
- Creative shot sequence is now the source of truth for timeline ordering.
- Each selected clip carries a creative intent and semantic intent-fit score.
- Unmatched creative beats are explicitly recorded instead of silently inventing footage.
- Storyboard reads the actual timeline intent, preserving sequence decisions after edits.
- UI exposes the Director's ordered story sequence before rendering.
- API version is 0.10.0.

## Next — v0.10 Stock/B-roll Gap Detection
- Compare required creative beats against available footage.
- Identify missing required shots such as CTA/exterior or proof footage.
- Generate practical stock-footage search requirements from the missing intent.
- Keep the gap report explainable and editable before rendering.


## v0.10 — Stock/B-roll Gap Detection
- Added an explainable footage-gap detector comparing required brief beats with the selected creative sequence and available semantic evidence.
- Required gaps such as missing CTA/exterior footage are surfaced explicitly instead of being silently substituted.
- Each missing beat includes a practical stock/B-roll search hint and semantic intent-fit evidence.
- Plan API exposes `footage_gaps`; the UI surfaces required gaps before rendering.


## v0.11 — Beat-aware Pacing
- Added a deterministic pacing allocator that assigns screen time by creative beat and requested pace.
- Energetic ads keep hook/CTA and supporting cuts tight; balanced ads allow experience/proof beats more room.
- Pacing respects the requested total duration and existing per-clip limits.
