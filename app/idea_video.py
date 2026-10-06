from __future__ import annotations
import asyncio, json, os, re, subprocess, textwrap, urllib.request
from pathlib import Path
from uuid import uuid4
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent.parent
DATA_ROOT=Path(os.getenv("NAHAVIDEO_DATA_DIR",str(ROOT/"data")))
STUDIO_ROOT=DATA_ROOT/"studio"
STUDIO_ROOT.mkdir(parents=True,exist_ok=True)

def _font(size,bold=False):
    p="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    try:return ImageFont.truetype(p,size)
    except OSError:return ImageFont.load_default()

def _rgb(v):
    v=v.lstrip("#")
    return tuple(int(v[i:i+2],16) for i in (0,2,4))

def _gradient(size,a,b):
    img=Image.new("RGB",size); pa=_rgb(a); pb=_rgb(b); px=img.load()
    for y in range(size[1]):
        t=y/max(1,size[1]-1); c=tuple(int(pa[i]*(1-t)+pb[i]*t) for i in range(3))
        for x in range(size[0]):px[x,y]=c
    return img

def _clean(v,f):
    v=re.sub(r"\s+"," ",str(v or "")).strip()
    return v or f

def _parse_json(text):
    text=text.strip()
    try:return json.loads(text)
    except json.JSONDecodeError:
        m=re.search(r"\{.*\}",text,re.S)
        try:return json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:return None

def _llm(idea,audience,cta,duration,fmt):
    base=(os.getenv("NAHALLM_BASE_URL") or os.getenv("NAHAVIDEO_LLM_BASE_URL") or "").rstrip("/")
    key=os.getenv("NAHALLM_API_KEY") or os.getenv("NAHAVIDEO_LLM_API_KEY") or ""
    model=os.getenv("NAHALLM_MODEL") or os.getenv("NAHAVIDEO_LLM_MODEL") or ""
    if not base or not model:return None
    prompt=f"""Create a spoken-word YouTube video plan.
IDEA: {idea}
AUDIENCE: {audience or "general audience"}
CTA: {cta or "Learn more"}
DURATION: {duration} seconds
FORMAT: {fmt}
Return JSON only with title, description, tags, hook and scenes[]. Each scene has on_screen, narration and visual.
Sound like a real South African creator, not corporate AI. No unsupported claims. Keep narration short enough for the duration."""
    body=json.dumps({"model":model,"messages":[{"role":"system","content":"Return valid JSON only."},{"role":"user","content":prompt}],"temperature":0.6,"max_tokens":1800}).encode()
    req=urllib.request.Request(f"{base}/chat/completions",data=body,headers={"Content-Type":"application/json","Authorization":f"Bearer {key}"},method="POST")
    try:
        with urllib.request.urlopen(req,timeout=45) as r:data=json.loads(r.read().decode())
        return _parse_json(data.get("choices",[{}])[0].get("message",{}).get("content",""))
    except Exception:return None

def _fallback(idea,audience,cta,duration,fmt):
    i=_clean(idea,"an idea worth explaining"); a=_clean(audience,"people who need a practical answer"); c=_clean(cta,"Follow NahaLabs for more practical systems.")
    lines=[f"Here is the useful part about {i}.",
           f"For {a}, the real problem is usually not a lack of information. It is knowing what to do next.",
           "So let us break it into a simple sequence you can actually use.",
           "Start by identifying the decision that matters most, then remove the steps that do not change the outcome.",
           "Once that is clear, the process becomes easier to measure, improve and repeat.",c]
    labels=["THE IDEA","THE PROBLEM","THE SHIFT","THE METHOD","THE RESULT","NEXT STEP"]
    return {"title":(i.title()+" — explained simply")[:90],"description":f"{i}\n\nA practical explanation from NahaVideo.\n\n{c}",
            "tags":["NahaLabs","NahaVideo","artificial intelligence","business","systems"],"hook":lines[0],
            "scenes":[{"on_screen":labels[n],"narration":lines[n],"visual":"clean editorial motion graphic"} for n in range(6)],
            "generation_mode":"deterministic_fallback","audience":a,"format":fmt,"duration":duration}

def generate_blueprint(idea,audience,cta,duration,fmt):
    duration=max(15,min(int(duration or 45),300))
    data=_llm(idea,audience,cta,duration,fmt) or _fallback(idea,audience,cta,duration,fmt)
    scenes=data.get("scenes") if isinstance(data.get("scenes"),list) else []
    scenes=[{"on_screen":_clean(s.get("on_screen"),"THE IDEA")[:70],
             "narration":_clean(s.get("narration"),"Here is the key point.")[:700],
             "visual":_clean(s.get("visual"),"editorial motion graphic")[:160]} for s in scenes[:10] if isinstance(s,dict)]
    if not scenes:
        data=_fallback(idea,audience,cta,duration,fmt); scenes=data["scenes"]
    data["scenes"]=scenes
    data["title"]=_clean(data.get("title"),_clean(idea,"NahaVideo"))[:90]
    data["description"]=_clean(data.get("description"),data["title"])[:5000]
    data["tags"]=[str(x).strip()[:40] for x in (data.get("tags") if isinstance(data.get("tags"),list) else []) if str(x).strip()][:15]
    data["generation_mode"]=data.get("generation_mode","nahallm"); data["duration"]=duration; data["format"]=fmt
    return data

async def _tts(text,out,voice):
    import edge_tts
    await edge_tts.Communicate(text,voice=voice,rate="+0%").save(str(out))

def _scene(path,size,idx,total,label,narration,visual):
    palettes=[("0B0D10","1B2430","D6A75D"),("0C1117","243447","8FCB9B"),("0E1114","33251E","E5B56B"),("0A1115","18313A","7FC7C2"),("11100E","302B25","F0C57A"),("0B0E12","1E2835","A8B7FF")]
    s,e,accent=palettes[idx%len(palettes)]; img=_gradient(size,s,e); d=ImageDraw.Draw(img); w,h=size; ar=_rgb(accent)
    for x in range(0,w,max(80,w//12)):d.line((x,0,x,h),fill=(255,255,255,10),width=1)
    for y in range(0,h,max(80,h//10)):d.line((0,y,w,y),fill=(255,255,255,10),width=1)
    m=max(50,w//12); small=_font(max(18,w//55),True); head=_font(max(54,w//12),True); body=_font(max(24,w//34))
    d.text((m,m),f"NAHAVIDEO / {idx+1:02d}",font=small,fill=ar)
    d.text((m,int(h*.28)),label.upper(),font=head,fill=(245,245,243))
    d.multiline_text((m,int(h*.52)),"\n".join(textwrap.wrap(narration,width=32 if w<1000 else 46)),font=body,fill=(222,226,230),spacing=12)
    d.text((m,int(h*.86)),_clean(visual,"editorial motion graphic")[:80],font=small,fill=(170,180,190))
    y=h-max(28,h//24); d.rounded_rectangle((m,y,w-m,y+8),radius=4,fill=(255,255,255,30))
    end=m+int((w-2*m)*max(.05,(idx+1)/total)); d.rounded_rectangle((m,y,end,y+8),radius=4,fill=ar)
    img.save(path,"PNG",optimize=True)

def _run(cmd):
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=600)
    if p.returncode:raise RuntimeError(p.stderr[-5000:] or "FFmpeg failed")

def _duration(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",str(path)],capture_output=True,text=True,timeout=60)
    try:return max(.1,float(p.stdout.strip()))
    except ValueError:return .1

def create_video_from_idea(idea,audience="",cta="",duration=45,format_name="youtube",voice="en-ZA-LeahNeural"):
    idea=_clean(idea,"")
    if not idea:raise ValueError("An idea is required")
    fmt=format_name if format_name in {"youtube","shorts"} else "youtube"
    bp=generate_blueprint(idea,audience,cta,duration,fmt)
    jid=uuid4().hex[:12]; job=STUDIO_ROOT/jid; job.mkdir(parents=True,exist_ok=True)
    voice=voice or os.getenv("NAHAVIDEO_VIDEO_VOICE","en-ZA-LeahNeural")
    narration=" ".join(s["narration"] for s in bp["scenes"]); audio=job/"voice.mp3"
    try:asyncio.run(_tts(narration,audio,voice))
    except Exception as e:raise RuntimeError(f"Voice generation failed: {type(e).__name__}: {e}")
    ad=_duration(audio); weights=[max(1,len(s["narration"].split())) for s in bp["scenes"]]; tw=sum(weights) or 1
    durations=[max(1.8,ad*w/tw) for w in weights]; size=(1280,720) if fmt=="youtube" else (720,1280)
    images=[]
    for i,s in enumerate(bp["scenes"]):
        p=job/f"scene_{i:02d}.png"; _scene(p,size,i,len(bp["scenes"]),s["on_screen"],s["narration"],s["visual"]); images.append(p)
    concat=job/"images.txt"; lines=[]
    for p,sd in zip(images,durations):lines += [f"file '{p.as_posix()}'",f"duration {sd:.3f}"]
    if images:lines += [f"file '{images[-1].as_posix()}'"]
    concat.write_text("\n".join(lines)+"\n",encoding="utf-8")
    silent=job/"silent.mp4"; out=job/"video.mp4"; scale="1280:720" if fmt=="youtube" else "720:1280"
    _run(["ffmpeg","-y","-v","error","-f","concat","-safe","0","-i",str(concat),"-vf",f"scale={scale}:force_original_aspect_ratio=decrease,pad={scale}:(ow-iw)/2:(oh-ih)/2,format=yuv420p","-r","30","-c:v","libx264","-preset","veryfast","-crf","25","-movflags","+faststart",str(silent)])
    _run(["ffmpeg","-y","-v","error","-i",str(silent),"-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(out)])
    bp.update({"voice":voice,"audio_duration_seconds":round(ad,2),"video_duration_seconds":round(_duration(out),2),"file":str(out),"job_id":jid})
    (job/"blueprint.json").write_text(json.dumps(bp,indent=2),encoding="utf-8")
    return bp
