# NahaVideo AI Director — v0.2 Build Plan

## Goal
Move from deterministic filename heuristics to a real local media-analysis loop while keeping the renderer provider-neutral.

## v0.2 shipped
- Local frame sampling with OpenCV.
- Real visual-quality scoring: exposure, contrast, saturation, sharpness.
- Lightweight scene-change detection from frame histograms.
- Audio activity/silence analysis using librosa.
- Hero-window selection based on active audio and visual hero timestamp.
- Optional background music upload.
- FFmpeg music ducking against the video's existing audio.
- Generated NahaLabs end card.
- Browser metrics showing visual score, scene count and silence ratio.
- Packaging/test configuration fixed for direct pytest execution.

## Explicit limitations
- No semantic food/object recognition yet; filename hints remain a prior.
- Speech transcription is not yet enabled by default.
- Dialogue/music separation assumes the video's original audio is the foreground signal.
- Generated end card is a placeholder for the real NahaLabs logo asset.

## v0.3 target
1. Optional local vision-language model adapter (OpenCLIP / Qwen-VL class models).
2. Whisper/faster-whisper transcript adapter.
3. Word/timestamp-aware dead-time removal.
4. Better dialogue detection and ducking envelope.
5. User-editable timeline decisions before render.
6. Real NahaLabs logo upload/branding kit.
