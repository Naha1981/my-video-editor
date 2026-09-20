import json, subprocess
from pathlib import Path
from .analysis import analyze_video, analyze_audio_intelligence
from .motion import render_brand_card


def ffprobe(path: Path) -> dict:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration:stream=width,height,r_frame_rate,codec_type,channels",
        "-of", "json", str(path)
    ]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffprobe failed")
    data = json.loads(p.stdout)
    duration = float(data.get("format", {}).get("duration", 0) or 0)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    rate = video.get("r_frame_rate", "0/1")
    try:
        a, b = rate.split("/")
        fps = float(a) / float(b) if float(b) else 0
    except Exception:
        fps = 0
    return {
        "duration": duration,
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
        "fps": fps,
        "has_audio": any(s.get("codec_type") == "audio" for s in data.get("streams", [])),
    }


def analyze_media(path: Path) -> dict:
    result = analyze_video(path)
    if ffprobe(path).get("has_audio"):
        intelligence = analyze_audio_intelligence(path)
    else:
        intelligence = {
            "audio": {"available": False, "active_ranges": [], "silence_ratio": 0.0},
            "transcript": {"available": False, "enabled": False, "segments": [], "speech_ranges": [], "reason": "no audio"},
        }
    result.update(intelligence)
    return result


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if p.returncode != 0:
        raise RuntimeError(p.stderr[-5000:] or "ffmpeg command failed")


def _escape_concat(path: Path) -> str:
    return path.as_posix().replace("'", "'\\''")


def _write_logo_card(temp: Path, duration: float, logo: Path | None = None) -> Path:
    card = temp / f"logo_card_{int(duration * 1000)}.mp4"
    draw = (
        "drawtext=text='NAHALABS':fontcolor=white:fontsize=92:"
        "x=(w-text_w)/2:y=(h-text_h)/2+250,"
        "drawtext=text='AI OPPORTUNITY ENGINEERING':fontcolor=0xB7C3D0:fontsize=28:"
        "x=(w-text_w)/2:y=(h-text_h)/2+375"
    )
    if logo and logo.exists():
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=0b0d0f:s=1080x1920:r=30",
            "-loop", "1", "-i", str(logo),
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(duration),
            "-filter_complex",
            f"[1:v]scale=460:460:force_original_aspect_ratio=decrease[lg];"
            f"[0:v][lg]overlay=(W-w)/2:(H-h)/2-120,{draw}[v]",
            "-map", "[v]", "-map", "2:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", str(card),
        ])
    else:
        _run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=0b0d0f:s=1080x1920:r=30",
            "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
            "-t", str(duration), "-vf", draw,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-shortest", str(card),
        ])
    return card


def _duck_expression(ranges: list[list[float]]) -> str:
    expression = "0.42"
    for start, end in reversed(ranges[:80]):
        expression = f"if(between(t,{float(start):.3f},{float(end):.3f}),0.12,{expression})"
    return expression


def _write_srt(temp: Path, captions: list[dict]) -> Path | None:
    if not captions:
        return None
    path = temp / "captions.srt"
    def ts(value: float) -> str:
        ms=max(0,int(round(float(value)*1000)))
        h,ms=divmod(ms,3600000); mi,ms=divmod(ms,60000); s,ms=divmod(ms,1000)
        return f"{h:02d}:{mi:02d}:{s:02d},{ms:03d}"
    lines=[]
    for i,c in enumerate(captions,1):
        text=str(c.get("text","")).strip().replace("\n"," ")
        if not text: continue
        lines += [str(i), f"{ts(c.get('start',0))} --> {ts(c.get('end',0))}", text, ""]
    path.write_text("\n".join(lines),encoding="utf-8")
    return path


def _subtitle_filter(path: Path) -> str:
    value=path.as_posix().replace("\\","/").replace(":","\\:").replace("'","\\'")
    return f"subtitles='{value}':force_style='FontName=Arial,FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=120'"


def render(
    project_dir: Path,
    plan: dict,
    clips: dict[str, Path],
    output: Path,
    music: Path | None = None,
    logo: Path | None = None,
    captions: bool = True,
) -> None:
    temp = project_dir / "render_parts"
    temp.mkdir(exist_ok=True)
    parts = []
    caption_path = _write_srt(temp, plan.get("captions", [])) if captions else None
    for i, item in enumerate(plan.get("timeline", [])):
        if item.get("enabled", True) is False:
            continue
        part = temp / f"part_{i:03d}.mp4"
        if item.get("type") == "logo":
            parts.append(render_brand_card(temp, float(item["duration"]), logo))
            continue
        if item.get("type") != "clip":
            continue
        src = clips[item["clip_id"]]
        duration = float(item["duration"])
        start = float(item.get("source_start", 0))
        filters = "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2"
        if caption_path:
            filters += "," + _subtitle_filter(caption_path)
        _run([
            "ffmpeg","-y","-v","error","-ss",str(start),"-i",str(src),"-t",str(duration),
            "-vf",filters,"-r","30","-c:v","libx264","-preset","veryfast","-crf","23",
            "-c:a","aac","-ar","48000","-ac","2",str(part)
        ])
        parts.append(part)

    if not parts:
        raise RuntimeError("No renderable clips in timeline")

    concat = temp / "concat.txt"
    concat.write_text("\n".join(f"file '{_escape_concat(p)}'" for p in parts),encoding="utf-8")
    base = temp / "base.mp4"
    _run([
        "ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(concat),
        "-vf","format=yuv420p","-r","30","-c:v","libx264","-preset","veryfast","-crf","23",
        "-c:a","aac","-ar","48000","-ac","2",str(base)
    ])

    if not music:
        output.unlink(missing_ok=True); base.replace(output); return

    duck_ranges=plan.get("audio",{}).get("duck_ranges",[])
    if duck_ranges:
        expression=_duck_expression(duck_ranges)
        filter_complex=f"[1:a]volume={expression}:eval=frame[music];[0:a][music]amix=inputs=2:duration=first:weights='1 0.8'[mix]"
    else:
        filter_complex="[1:a]volume=0.42[music];[music][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=25:release=280[ducked];[0:a][ducked]amix=inputs=2:duration=first:weights='1 0.8'[mix]"
    _run([
        "ffmpeg","-y","-v","error","-i",str(base),"-stream_loop","-1","-i",str(music),
        "-filter_complex",filter_complex,"-map","0:v:0","-map","[mix]",
        "-c:v","copy","-c:a","aac","-ar","48000","-shortest",str(output)
    ])
