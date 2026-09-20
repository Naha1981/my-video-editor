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

Current milestone: v0.2 foundation.

## Status

See `plan.md` for the implementation roadmap.

## v0.3 AI Director

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
