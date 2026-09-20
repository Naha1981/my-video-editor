import json, subprocess
from pathlib import Path
from .analysis import analyze_video, detect_active_audio

def ffprobe(path:Path)->dict:
    cmd=["ffprobe","-v","error","-show_entries","format=duration:stream=width,height,r_frame_rate,codec_type,channels","-of","json",str(path)]
    p=subprocess.run(cmd,capture_output=True,text=True)
    if p.returncode!=0:raise RuntimeError(p.stderr.strip() or "ffprobe failed")
    data=json.loads(p.stdout);duration=float(data.get("format",{}).get("duration",0) or 0)
    video=next((s for s in data.get("streams",[]) if s.get("codec_type")=="video"),{});rate=video.get("r_frame_rate","0/1")
    try:a,b=rate.split("/");fps=float(a)/float(b) if float(b) else 0
    except Exception:fps=0
    return {"duration":duration,"width":int(video.get("width",0) or 0),"height":int(video.get("height",0) or 0),
            "fps":fps,"has_audio":any(s.get("codec_type")=="audio" for s in data.get("streams",[]))}

def analyze_media(path:Path)->dict:
    visual=analyze_video(path)
    audio=detect_active_audio(path) if ffprobe(path).get("has_audio") else {"available":False,"active_ranges":[],"silence_ratio":0.0}
    visual["audio"]=audio;return visual

def _run(cmd:list[str])->None:
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=300)
    if p.returncode!=0:raise RuntimeError(p.stderr[-5000:] or "ffmpeg command failed")

def _escape_concat(path:Path)->str:return path.as_posix().replace("'","'\\''")

def _write_logo_card(temp:Path,duration:float)->Path:
    card=temp/"logo_card.mp4"
    draw="drawtext=text='NAHALABS':fontcolor=white:fontsize=92:x=(w-text_w)/2:y=(h-text_h)/2-40,drawtext=text='AI OPPORTUNITY ENGINEERING':fontcolor=0xB7C3D0:fontsize=28:x=(w-text_w)/2:y=(h-text_h)/2+70"
    _run(["ffmpeg","-y","-v","error","-f","lavfi","-i","color=c=0b0d0f:s=1080x1920:r=30","-f","lavfi","-i","anullsrc=r=48000:cl=stereo","-t",str(duration),"-vf",draw,"-map","0:v:0","-map","1:a:0","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-ar","48000","-ac","2","-shortest",str(card)])
    return card

def render(project_dir:Path,plan:dict,clips:dict[str,Path],output:Path,music:Path|None=None)->None:
    temp=project_dir/"render_parts";temp.mkdir(exist_ok=True);parts=[]
    for i,item in enumerate(plan["timeline"]):
        if item["type"]!="clip":continue
        src=clips[item["clip_id"]];part=temp/f"part_{i:03d}.mp4";duration=float(item["duration"]);start=float(item.get("source_start",0))
        _run(["ffmpeg","-y","-v","error","-ss",str(start),"-i",str(src),"-t",str(duration),
              "-vf","scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
              "-r","30","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-ar","48000","-ac","2",str(part)])
        parts.append(part)
    for item in plan["timeline"]:
        if item["type"]=="logo":parts.append(_write_logo_card(temp,float(item["duration"])))
    if not parts:raise RuntimeError("No renderable clips in timeline")
    concat=temp/"concat.txt";concat.write_text("\n".join(f"file '{_escape_concat(p)}'" for p in parts),encoding="utf-8");base=temp/"base.mp4"
    _run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(concat),"-vf","format=yuv420p","-r","30","-c:v","libx264","-preset","veryfast","-crf","23","-c:a","aac","-ar","48000","-ac","2",str(base)])
    if not music:output.unlink(missing_ok=True);base.replace(output);return
    _run(["ffmpeg","-y","-v","error","-i",str(base),"-stream_loop","-1","-i",str(music),"-filter_complex",
          "[1:a]volume=0.42[music];[music][0:a]sidechaincompress=threshold=0.03:ratio=8:attack=25:release=280[ducked];[0:a][ducked]amix=inputs=2:duration=first:weights='1 0.8'[mix]",
          "-map","0:v:0","-map","[mix]","-c:v","copy","-c:a","aac","-ar","48000","-shortest",str(output)])
