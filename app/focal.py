from __future__ import annotations

from pathlib import Path
from typing import Any
import cv2
import numpy as np
import subprocess


def focal_point(path: Path, sample_time: float = 0.0) -> dict[str, Any]:
    """Estimate a safe crop focal point with lightweight local CV; no model required."""
    cmd=["ffmpeg","-v","error","-ss",str(max(0.0,sample_time)),"-i",str(path),"-frames:v","1","-vf","scale=640:-2","-f","image2pipe","-vcodec","mjpeg","-"]
    p=subprocess.run(cmd,capture_output=True,timeout=30)
    frame=cv2.imdecode(np.frombuffer(p.stdout,dtype=np.uint8),cv2.IMREAD_COLOR) if p.returncode==0 else None
    if frame is None:
        return {"x":0.5,"y":0.5,"confidence":0.0,"method":"center-fallback"}
    h,w=frame.shape[:2]
    gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
    face=cv2.CascadeClassifier(str(Path(cv2.data.haarcascades)/"haarcascade_frontalface_default.xml"))
    faces=face.detectMultiScale(gray,1.1,5,minSize=(32,32))
    if len(faces):
        areas=[ww*hh for _,_,ww,hh in faces]
        x,y,ww,hh=faces[int(np.argmax(areas))]
        return {"x":round((x+ww/2)/w,4),"y":round((y+hh/2)/h,4),"confidence":0.85,"method":"face"}
    # Lightweight visual saliency proxy: local contrast + edges, weighted away from borders.
    blur=cv2.GaussianBlur(gray,(0,0),7)
    score=cv2.absdiff(gray,blur).astype(np.float32)
    edges=cv2.Canny(gray,80,160).astype(np.float32)
    score=score*0.7+edges*0.3
    yy,xx=np.mgrid[0:h,0:w]
    border=np.minimum.reduce([xx,yy,w-1-xx,h-1-yy]).astype(np.float32)
    score*=np.clip(border/max(1.0,min(w,h)*0.18),0.15,1.0)
    total=float(score.sum())
    if total<=0:
        return {"x":0.5,"y":0.5,"confidence":0.0,"method":"center-fallback"}
    px=float((score*xx).sum()/total)/w
    py=float((score*yy).sum()/total)/h
    return {"x":round(float(np.clip(px,0.2,0.8)),4),"y":round(float(np.clip(py,0.2,0.8)),4),
            "confidence":round(float(min(0.7,total/(w*h*18))),3),"method":"contrast-edge"}


def crop_filter(width: int, height: int, focal: dict[str, Any] | None = None) -> str:
    x=float((focal or {}).get("x",0.5))
    y=float((focal or {}).get("y",0.5))
    # Scale to fill, then bias crop toward the detected focal point.
    crop_x=f"clip(iw*{x:.4f}-{width}/2,0,iw-{width})"
    crop_y=f"clip(ih*{y:.4f}-{height}/2,0,ih-{height})"
    return f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}:{crop_x}:{crop_y},setsar=1"
