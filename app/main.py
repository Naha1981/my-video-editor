from pathlib import Path
from uuid import uuid4
import shutil
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .media import ffprobe, analyze_media, render
from .director import Clip, build_plan

ROOT=Path(__file__).resolve().parent.parent;MEDIA=ROOT/"media";MEDIA.mkdir(exist_ok=True)
app=FastAPI(title="NahaVideo AI Director",version="0.2.0")

class PlanRequest(BaseModel):
    prompt:str;duration:int=30;clip_ids:list[str];music_id:str|None=None
class RenderRequest(BaseModel):
    plan:dict;clip_ids:list[str];music_id:str|None=None

def _find_media(mid:str):
    matches=list(MEDIA.glob(f"{mid}.*"));return matches[0] if matches else None

@app.get("/api/health")
def health():return {"ok":True,"product":"NahaVideo AI Director","version":"0.2.0"}

@app.post("/api/upload")
async def upload(files:list[UploadFile]=File(...)):
    results=[];allowed={".mp4",".mov",".m4v",".webm",".avi",".mkv"}
    for f in files:
        suffix=Path(f.filename or "").suffix.lower()
        if suffix not in allowed:raise HTTPException(400,f"Unsupported video type: {suffix}")
        cid=uuid4().hex[:12];path=MEDIA/f"{cid}{suffix}"
        with path.open("wb") as out:shutil.copyfileobj(f.file,out)
        try:meta=ffprobe(path);analysis=analyze_media(path)
        except Exception as e:path.unlink(missing_ok=True);raise HTTPException(400,str(e))
        results.append({"id":cid,"filename":f.filename,"path":str(path),**meta,"analysis":analysis})
    return results

@app.post("/api/upload-music")
async def upload_music(file:UploadFile=File(...)):
    suffix=Path(file.filename or "").suffix.lower()
    if suffix not in {".mp3",".wav",".m4a",".aac",".ogg",".flac"}:raise HTTPException(400,f"Unsupported music type: {suffix}")
    mid=uuid4().hex[:12];path=MEDIA/f"{mid}{suffix}"
    with path.open("wb") as out:shutil.copyfileobj(file.file,out)
    try:meta=ffprobe(path)
    except Exception as e:path.unlink(missing_ok=True);raise HTTPException(400,str(e))
    return {"id":mid,"filename":file.filename,"duration":meta["duration"]}

@app.post("/api/plan")
def plan(req:PlanRequest):
    clips=[]
    for cid in req.clip_ids:
        path=_find_media(cid)
        if not path:raise HTTPException(404,f"Clip not found: {cid}")
        meta=ffprobe(path);analysis=analyze_media(path)
        clips.append(Clip(cid,path.name,str(path),meta["duration"],meta["width"],meta["height"],meta["fps"],analysis))
    result=build_plan(clips,req.prompt,req.duration)
    result["audio"]["background_music"]=bool(req.music_id and _find_media(req.music_id));result["audio"]["music_id"]=req.music_id
    return result

@app.post("/api/render")
def render_video(req:RenderRequest):
    clips={cid:_find_media(cid) for cid in req.clip_ids};clips={k:v for k,v in clips.items() if v}
    if not clips:raise HTTPException(404,"No clips found")
    music=_find_media(req.music_id) if req.music_id else None;rid=uuid4().hex[:12];output=MEDIA/f"nahavideo_{rid}.mp4"
    try:render(MEDIA,req.plan,clips,output,music)
    except Exception as e:raise HTTPException(500,str(e))
    return {"id":rid,"download":f"/api/render/{rid}"}

@app.get("/api/render/{rid}")
def download_render(rid:str):
    path=MEDIA/f"nahavideo_{rid}.mp4"
    if not path.exists():raise HTTPException(404,"Render not found")
    return FileResponse(path,media_type="video/mp4",filename=path.name)

app.mount("/",StaticFiles(directory=str(ROOT/"app"/"static"),html=True),name="static")
