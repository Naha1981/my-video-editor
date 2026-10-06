from __future__ import annotations
import os, secrets, time
from pathlib import Path
from typing import Any

SCOPES=["https://www.googleapis.com/auth/youtube.upload"]
STATES={}
ROOT=Path(__file__).resolve().parent.parent
DATA_ROOT=Path(os.getenv("NAHAVIDEO_DATA_DIR",str(ROOT/"data")))
YT=DATA_ROOT/"youtube"; YT.mkdir(parents=True,exist_ok=True)
TOKEN=YT/"token.json"

def _config():
    cid=os.getenv("YOUTUBE_CLIENT_ID","").strip()
    secret=os.getenv("YOUTUBE_CLIENT_SECRET","").strip()
    if not cid or not secret:return None
    return {"web":{"client_id":cid,"client_secret":secret,"auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token",
                   "redirect_uris":[os.getenv("YOUTUBE_REDIRECT_URI","https://my-video-editor-58vk.onrender.com/api/youtube/oauth/callback")]}}

def status():
    c=_config()
    return {"configured":bool(c),"authorized":TOKEN.exists(),"ready":bool(c and TOKEN.exists()),
            "redirect_uri":(c or {"web":{"redirect_uris":[None]}})["web"]["redirect_uris"][0],
            "scope":SCOPES[0],
            "privacy_note":"Unverified Google API projects may keep API-uploaded videos private until YouTube API compliance review."}

def authorization_url():
    c=_config()
    if not c:raise RuntimeError("Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET on Render first.")
    from google_auth_oauthlib.flow import Flow
    f=Flow.from_client_config(c,scopes=SCOPES,redirect_uri=c["web"]["redirect_uris"][0])
    state=secrets.token_urlsafe(32); STATES[state]=time.time()
    url,_=f.authorization_url(access_type="offline",include_granted_scopes="true",prompt="consent",state=state)
    return url

def handle_callback(code,state):
    issued=STATES.pop(state,None)
    if not issued or time.time()-issued>900:raise RuntimeError("OAuth state is missing or expired.")
    c=_config()
    if not c:raise RuntimeError("YouTube OAuth credentials are not configured.")
    from google_auth_oauthlib.flow import Flow
    f=Flow.from_client_config(c,scopes=SCOPES,redirect_uri=c["web"]["redirect_uris"][0])
    f.fetch_token(code=code); TOKEN.write_text(f.credentials.to_json(),encoding="utf-8")

def _creds():
    if not TOKEN.exists():return None
    from google.oauth2.credentials import Credentials
    c=Credentials.from_authorized_user_file(str(TOKEN),SCOPES)
    if c and c.expired and c.refresh_token:
        from google.auth.transport.requests import Request
        c.refresh(Request()); TOKEN.write_text(c.to_json(),encoding="utf-8")
    return c

def upload_video(path:Path,title:str,description:str,tags=None,privacy_status="private",category_id="22")->dict[str,Any]:
    c=_creds()
    if not c:raise RuntimeError("Connect the YouTube channel before publishing.")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    yt=build("youtube","v3",credentials=c)
    body={"snippet":{"title":title[:100],"description":description[:5000],"tags":[str(t)[:40] for t in (tags or [])][:15],"categoryId":str(category_id)},
          "status":{"privacyStatus":privacy_status if privacy_status in {"private","unlisted","public"} else "private","selfDeclaredMadeForKids":False}}
    req=yt.videos().insert(part="snippet,status",body=body,media_body=MediaFileUpload(str(path),mimetype="video/mp4",resumable=True))
    response=None
    while response is None:_,response=req.next_chunk()
    vid=response.get("id")
    return {"uploaded":bool(vid),"video_id":vid,"url":f"https://www.youtube.com/watch?v={vid}" if vid else None,
            "privacy_status":body["status"]["privacyStatus"],"resource":response}
