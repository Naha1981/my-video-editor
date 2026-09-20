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


## v0.12 — Multi-frame Semantic Intelligence
- OpenCLIP semantic evidence is aggregated across multiple sampled frames instead of relying on a simple frame average alone.
- Aggregation exposes conservative labels, peak evidence, temporal consistency, top semantic labels and the strongest individual frame.
- Director intent matching consumes the aggregated semantic labels, while explainable shot tags expose multi-frame evidence.
- A single contradictory frame is less likely to overturn the dominant visual story.


## v0.13 — Transcript + Audio-beat-aware Pacing
- Added local librosa beat detection for background music.
- Cut boundaries can move toward nearby music beats without knowingly cutting through transcript speech ranges.
- Dialogue safety takes precedence when a nearby beat conflicts with active speech.
- Pacing decisions are explainable: `beat_aligned`, `speech_safe`, `speech_preserved` and `unchanged`.
- The API exposes music BPM/beat timestamps and pacing decisions.
- The existing deterministic CPU/local-first path remains the fallback when beat analysis is unavailable.


## v0.14 — NahaLabs Motion Graphics Engine
- Brand end cards now render through a formal NahaLabs motion-engine adapter seam.
- The motion engine receives a stable brand context including NahaLabs identity, NahaVideo product identity, 1080x1920/30fps output requirements, duration and logo path.
- A proprietary motion renderer can be injected without changing the Director or FFmpeg media pipeline.
- The existing FFmpeg brand-card renderer remains the deterministic fallback when no proprietary engine is supplied.
- Added contract tests for engine context and missing-output handling.


## v0.15 — Per-shot Multi-frame Semantic Intelligence
- Added reusable temporal semantic analysis for individual shot/scene windows.
- Detected visual scene boundaries now define semantic analysis windows when local vision is enabled.
- Each window aggregates multiple frames, reducing dependence on a single lucky frame.
- Creative intent scoring can use the strongest verified semantic evidence from a specific shot window.
- The existing CPU-only path remains unchanged when OpenCLIP is disabled.
- Vision output now distinguishes whole-source semantic evidence from per-shot temporal evidence.


## v0.16 — Stock/B-roll Search Manifest
- Converts Director-detected missing footage into explicit stock search jobs.
- Each missing beat gets a semantic search query and provider-ready search destinations.
- Includes Pexels, Pixabay and Mixkit search routes without requiring API keys.
- Keeps stock acquisition explicit: the Director never silently invents or substitutes footage.
- API plans now expose a stock manifest alongside footage gaps.
- This adapter is the seam for future provider APIs and automatic asset ingestion.


## v0.17 — Stock Asset Ingestion
- Added a provenance-aware stock ingestion path for downloaded B-roll.
- Attached stock assets carry provider, source URL, license, attribution, beat and creative intent metadata in a sidecar file.
- Stock is explicitly approved by the user before the Director can select it automatically.
- Approved stock with an exact creative intent match receives deterministic intent-fit priority, allowing it to fill a detected footage gap.
- Pending/unapproved stock is excluded from automatic story selection.
- The Director exposes attached stock provenance in the plan and preserves the source asset as a first-class clip.
- The UI now supports attaching a downloaded stock clip, recording provenance and rebuilding the plan with the new asset.
- Media lookup ignores provenance sidecars so metadata files can never be rendered as video.
- Next media-execution layer: formal FFmpeg Skill adapter for probe → edit → verify without replacing the NahaVideo Director.


## v0.18 — Optional FFmpeg Skill Execution / QA Adapter
- Added a dependency-light adapter that discovers an installed ffmpeg-skill locally through the NAHAVIDEO_FFMPEG_SKILL_HOME environment variable, the standard Claude skill path, or local project folders.
- The adapter never invokes a shell; it calls the skill's typed Python tools directly.
- Rendered outputs can now be probed with probe.py and checked against a delivery platform with check.py.
- If the skill is unavailable, NahaVideo keeps using its native FFmpeg renderer and reports that fallback explicitly.
- The Director remains the creative brain; ffmpeg-skill is an optional deterministic execution/verification layer.


## v0.19 — NahaLabs Creative Command Context
- Added a reusable machine-readable NahaLabs context for product, commercial lane, campaign objective, format and authenticity profile.
- Supports commands such as `/cargoiq /lead-gen /facebook-ad /nahalabs-authentic`.
- Commercial lanes are explicit: Intelligent Solutions and Enterprise Intelligence.
- The Creative Director now receives this context before it builds the creative concept.
- Objective rules can alter the creative rule for lead generation, revenue recovery, proof, bookings, sales and awareness.
- The NahaLabs Authenticity profile carries South African realism, natural people, local environments and believable imperfections as production constraints.
- The context also exposes two reusable loops: Find → Understand → Act → Learn for system narratives, and Content → Distribution → Leads → Sales → Revenue → Analytics for growth workflows.
- The context is surfaced in the Director UI and can later be reused by website, advertising and broader Creative Growth OS tooling.


## v0.20 — Multi-platform Delivery Packs
- Added normalized delivery destinations for Reels, TikTok, YouTube Shorts, YouTube, LinkedIn, Facebook, X and Podcast.
- One NahaVideo edit decision graph now drives multiple platform outputs instead of rebuilding the creative for each destination.
- When ffmpeg-skill is installed, the delivery pack uses its platform templates and structured output workflow.
- When ffmpeg-skill is unavailable, NahaVideo keeps the native FFmpeg base render and reports the fallback explicitly.
- The API exposes a delivery-pack plan, base render and platform-specific download routes.
- The UI now lets the operator select delivery destinations and render a platform pack.
- Platform QA remains tied to the final output rather than assuming that a successful FFmpeg command means the asset is valid.


## v0.21 — NahaLabs Browser Asset Scout + NahaLLM
- Added an isolated NahaLLM client using the OpenAI-compatible gateway without adding provider-specific credentials to NahaVideo.
- Added an isolated Jev browser adapter with feature flag, URL validation, domain allowlist support, timeouts and structured mission results.
- Added a separate Jev Browser Worker container so Chromium/Browser Harness is never a hard dependency of the NahaVideo renderer.
- Added NahaLLM mission compilation with deterministic fallback when NahaLLM is disabled or unavailable.
- Added a first application mission: website asset scouting for business name, contact/CTA, booking/order routes, public brand images and useful pages.
- Added structured browser evidence with source URL, observation time and verification labels; raw model output is not treated as verified business data.
- Added a NahaLabs Asset Scout UI action so an operator can request asset collection instead of manually hunting through client websites.
- Jev remains the browser execution component; NahaVideo remains responsible for business/creative logic, validation and rendering.
- Jev's current TypeSafe operation/target model remains intact. NahaLLM can serve as its field-text helper and evidence interpretation layer through configuration.
- Added SSRF/private-network protections, worker API authentication, step/time budgets, and failure isolation.
- Existing application functionality remains the source of truth when `NAHALLM_ENABLED=0` and `JEV_ENABLED=0`.

### v0.21 Deployment shape
```
NahaVideo Web Service
    ├── existing Creative Director / media pipeline
    ├── optional NahaLLM client ──> NahaLLM Web Service
    └── optional Jev client ──────> Jev Browser Worker ──> Chromium / Browser Harness
```


## v0.22 — Automatic Asset Acquisition + Stock Scout
- Extended Jev Asset Scout to expose directly loaded public video media in addition to image/link candidates.
- Added a safety-bounded public asset collector with domain allowlisting, redirect validation, private-network blocking, content-type allowlisting and maximum download size.
- Downloaded video candidates are registered as pending stock with source provenance; they are never auto-approved for final use.
- Added Jev-driven stock missions for Director-detected missing footage across Pexels, Pixabay and Mixkit search destinations.
- Added a one-click NahaLabs stock scout so missing footage can be searched and candidate media collected without manual stock-site browsing.
- Approved collected stock now flows through the existing Director and delivery-pack paths.
- Existing renderer, Director, provenance model and feature-flag fallback remain intact.

- Auto-collected stock can be previewed and approved in place; no download/re-upload step is required.


## v0.23 — Customer-first production flow
- Added a one-click production workflow so the normal customer path is upload footage → optional website → describe outcome → Create video.
- The application now orchestrates website understanding, creative direction, footage-gap analysis, optional automatic stock scouting, and delivery rendering behind the simplified UI.
- The advanced Director, stock provenance and editable timeline controls remain available without being required for normal operation.
- Automatic stock remains pending until an operator confirms provenance/license; the base draft can render without blocking on that approval.


## v0.24 — Approved Stock Finalization
- Fixed the advanced plan flow so approved stock asset IDs are actually passed back into the Director.
- Added a one-click **Rebuild & Finalize with Approved Stock** workflow after operator approval.
- The Director re-runs sequence selection, footage-gap detection, pacing and captions with approved stock as first-class footage.
- Final delivery rendering uses only approved stock assets; pending stock remains excluded.
- Preserves the provenance-first rule: approval is explicit and traceable before automatic story selection.


## v0.25 — Cobalt Media Acquisition Adapter
- Added an optional Cobalt integration for authorized URL-based media acquisition.
- Cobalt is configured through `NAHAVIDEO_COBALT_API_URL` and is self-hosted-only by design; NahaVideo does not implicitly depend on a public Cobalt API.
- Added an explicit authorization confirmation before media acquisition.
- Cobalt responses are normalized into reviewable media candidates; picker responses remain choices and are not silently selected.
- Provenance remains attached to the original source URL/provider before any later approval/import workflow.
- Added browser UI for Paste URL → Import Media.
- Cobalt remains an optional acquisition adapter; NahaVideo's Director does not depend on it.


## v0.26 — Production Final QA
- Added a deterministic final QA gate before delivery.
- Checks required creative coverage, source-file availability, stock approval, stock provenance and timeline duration.
- Added `/api/final-qa` and a visible Final QA panel.
- QA produces explicit pass/block states rather than silently rendering an unsafe plan.
- Cobalt remains an acquisition layer; approval and provenance remain mandatory.


## v0.27 — Auditable Delivery Manifest
- Added a deterministic delivery manifest for the exact Director plan submitted to delivery.
- Records plan/version, creative direction, NahaLabs context, timeline, source assets, stock provenance, music/logo references, footage gaps and Final QA state.
- Source video files receive SHA-256 checksums so the delivered edit can be traced back to exact media bytes.
- Added /api/delivery-manifest and UI access from Final QA.


## v0.28 — Multi-format Variants
- Added deterministic approved-plan rendering into 9:16, 1:1 and 16:9 outputs.
- Variants are generated from the same sanitized Director timeline rather than independently inventing edits.
- Variant rendering is gated by the Final QA checks.
- Added downloadable variant routes and a one-click UI action.


## v0.29 — Intelligent Variant Reframing
- Added lightweight local focal-point detection for multi-format rendering.
- Face detection is preferred when a face is visible; otherwise a contrast/edge saliency proxy estimates the visual focal point.
- Variant crops are biased toward the detected focal point instead of blindly center-cropping.
- No new ML model dependency is required.


## v0.30 — Per-shot Intelligent Reframing
- Variant rendering now accepts the Director timeline and analyzes each shot independently.
- Each shot receives its own focal point before aspect-ratio cropping.
- Reframing decisions are exposed in the variant result metadata.
- The same approved edit remains the source of truth across all aspect ratios.


## v0.31 — Aspect-aware Caption Safe Zones
- Variant rendering now burns captions after reframing, rather than inheriting captions from the base render.
- 9:16, 1:1 and 16:9 receive conservative format-specific subtitle margins and sizing.
- Caption placement is deterministic and recorded in variant metadata.


## v0.32 — Smart Caption Segmentation
- Transcript captions are now split into short readable chunks using word and character limits.
- Chunk timing proportionally fills each source speech segment.
- The existing per-format safe zones remain responsible for final placement.
- Added deterministic caption segmentation tests.


## v0.33 — Restrained Caption Emphasis
- Caption chunks now identify a small set of meaningful commercial/emphasis words.
- Emphasis is metadata-first; no bouncing-word or noisy kinetic typography is introduced.
- Normal captions remain visually unchanged.
