# NahaVideo — AI Video Director

NahaLabs' local-first AI video editing system.

## Goal

Turn a natural-language creative brief into an executable video edit:

> Create a 30-second premium restaurant advertisement. Start with the strongest food shot, remove dead time, keep the pacing energetic, lower the music under dialogue, and finish with the NahaLabs logo.

## Architecture

- AI Director — converts creative intent into an edit decision graph
- Media Analysis — FFmpeg/OpenCV
- Scene & shot analysis
- Speech/silence analysis
- Timeline generation
- Audio ducking
- Motion graphics
- FFmpeg rendering

## Development

NahaVideo is designed to run locally and evolve toward CPU-friendly/open-source AI components.

Current milestone: v0.21 Browser Asset Scout + NahaLLM.

## Status

See `plan.md` for the implementation roadmap.

## v0.6 AI Director

The editor now has a model-optional intelligence layer:

- deterministic frame/audio analysis remains the default CPU-friendly path
- optional local faster-whisper adds timestamped speech/word intelligence
- optional local OpenCLIP adds zero-shot semantic shot relevance
- the Director emits an explainable edit decision graph
- the browser timeline can reorder, trim, remove and restore decisions before render
- transcript-aware music ducking is recalculated after timeline edits
- a supplied NahaLabs logo can be composited into the end card

### Optional model setup

Install `requirements-models.txt`, then enable the adapters with environment variables documented in `plan.md`.


## v0.20 shipped
- Local website URL intake extracts title, description and visible text using the Python standard library.
- Deterministic creative-brief compiler produces business category, offer, audience, tone, CTA and visual requirements.
- Stock-shot requirement generator turns the brief into a practical footage shopping list.
- Timeline rendering now preserves clip/logo order.
- Transcript captions can be burned into the rendered MP4 and are rebuilt after timeline edits.
- NahaLabs motion graphics now has an explicit adapter seam so the proprietary motion engine can replace the FFmpeg fallback.

### Website workflow
Client website URL → Brand intake → Creative brief → Shot requirements → Footage → AI Director → Storyboard → Captions → NahaLabs motion graphics → MP4

The website intake is intentionally deterministic and local-first. It does not claim to understand a site with an external LLM; the extracted brief remains editable and can later be connected to a local model.


## Creative Director
- Added a deterministic creative-direction engine that turns brand/brief context into an ad concept, hook, promise, proof path, CTA and shot sequence.
- Restaurant direction includes sensory hero, experience and signature concepts; general business direction includes outcome, problem→solution and proof concepts.
- The selected concept is attached to every edit plan and surfaced in the UI.
- Storyboard beats now carry explicit creative shot intent such as `hero_food`, `craft`, `proof`, `experience`, `result` and `cta`.
- Website intake now feeds the Creative Director before the editing plan is produced.
