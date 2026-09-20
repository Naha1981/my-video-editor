from pathlib import Path
from uuid import uuid4
import shutil
import json
import logging
import os
import time
import shutil as _shutil

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .media import ffprobe, analyze_media, render
from .director import Clip, build_plan, sanitize_plan
from .storyboard import build_storyboard, add_transcript_captions
from .brief import fetch_brand, compile_creative_brief
from .stock import shot_requirements
from .creative import creative_direction
from .gaps import detect_footage_gaps
from .beats import detect_beats
from .pacing import align_cut_boundaries
from .motion import render_brand_card
from .stock_search import build_stock_manifest
from .stock_ingest import register_stock_asset, enrich_analysis_with_stock, stock_public
from .naha_context import compile_context
from .ffmpeg_skill import available as ffmpeg_skill_available, verify_output
from .delivery import build_delivery_pack, normalize_platforms, render_delivery_pack, validate_final_plan, build_delivery_manifest
from .variants import render_variants
from .rationale import build_edit_rationale
from .projects import save_project, load_project, list_projects, normalize_project_id
from .security import client_ip, env_int, validate_public_url
from .auth import enabled as auth_enabled, issue_session, valid_session, cookie_options
from .integrations.nahallm import NahaLLMClient
from .integrations.jev import JevBrowserAgent
from .services.asset_scout import scout_website_assets
from .services.asset_fetcher import collect_public_assets
from .services.stock_scout import scout_missing_stock
from .integrations.cobalt import configured as cobalt_configured, request_media, normalize_candidates, candidate_download_allowed, CobaltError

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_ROOT = Path("/var/data") if Path("/var/data").exists() else ROOT / "data"
DATA_ROOT = Path(os.getenv("NAHAVIDEO_DATA_DIR", str(DEFAULT_DATA_ROOT)))
MEDIA = DATA_ROOT / "media"
PROJECTS = DATA_ROOT / "projects"
MEDIA.mkdir(parents=True, exist_ok=True)
PROJECTS.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("nahavideo")
logging.basicConfig(
    level=os.getenv("NAHAVIDEO_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s nahavideo %(message)s",
)

MAX_VIDEO_UPLOAD_BYTES = env_int("NAHAVIDEO_MAX_VIDEO_UPLOAD_BYTES", 250 * 1024 * 1024, maximum=2 * 1024 * 1024 * 1024)
MAX_STOCK_UPLOAD_BYTES = env_int("NAHAVIDEO_MAX_STOCK_UPLOAD_BYTES", 250 * 1024 * 1024, maximum=2 * 1024 * 1024 * 1024)
MAX_AUDIO_UPLOAD_BYTES = env_int("NAHAVIDEO_MAX_AUDIO_UPLOAD_BYTES", 100 * 1024 * 1024, maximum=512 * 1024 * 1024)
MAX_LOGO_UPLOAD_BYTES = env_int("NAHAVIDEO_MAX_LOGO_UPLOAD_BYTES", 10 * 1024 * 1024, maximum=100 * 1024 * 1024)
RATE_LIMIT_PER_MINUTE = env_int("NAHAVIDEO_RATE_LIMIT_PER_MINUTE", 120, maximum=1000)
_rate_buckets: dict[str, list[float]] = {}
_request_metrics = {"requests": 0, "api_requests": 0, "errors": 0, "renders": 0}

app = FastAPI(title="NahaVideo AI Director", version="0.43.0")

@app.middleware("http")
async def production_guard(request: Request, call_next):
    started = time.perf_counter()
    request_id = uuid4().hex[:12]
    path = request.url.path
    is_api = path.startswith("/api/")
    if is_api:
        _request_metrics["api_requests"] += 1
        protected = (
            request.method not in {"GET", "HEAD", "OPTIONS"}
            and any(path.startswith(prefix) for prefix in {
                "/api/upload", "/api/plan", "/api/render", "/api/variants",
                "/api/projects", "/api/stock-scout", "/api/asset-scout",
                "/api/cobalt", "/api/assets",
            })
            and path not in {"/api/login", "/api/auth/status"}
        )
        if protected and auth_enabled() and not valid_session(request.cookies.get("nahavideo_session")):
            return JSONResponse(
                {"detail": "Authentication required."},
                status_code=401,
                headers={"X-Request-ID": request_id},
            )
        ip = client_ip(request)
        now = time.monotonic()
        bucket = [t for t in _rate_buckets.get(ip, []) if now - t < 60]
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            if len(bucket) >= RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    {"detail": "Too many requests. Please slow down and try again."},
                    status_code=429,
                    headers={"Retry-After": "60", "X-Request-ID": request_id},
                )
            bucket.append(now)
            _rate_buckets[ip] = bucket

        content_length = request.headers.get("content-length")
        if content_length:
            try:
                declared = int(content_length)
            except ValueError:
                declared = 0
            limits = {
                "/api/upload": MAX_VIDEO_UPLOAD_BYTES * 6,
                "/api/upload-stock": MAX_STOCK_UPLOAD_BYTES + 2 * 1024 * 1024,
                "/api/upload-music": MAX_AUDIO_UPLOAD_BYTES + 2 * 1024 * 1024,
                "/api/upload-logo": MAX_LOGO_UPLOAD_BYTES + 1024 * 1024,
            }
            limit = limits.get(path)
            if limit is not None and declared > limit:
                return JSONResponse(
                    {"detail": "Upload exceeds the configured request-size limit."},
                    status_code=413,
                    headers={"X-Request-ID": request_id},
                )

    _request_metrics["requests"] += 1
    try:
        response = await call_next(request)
    except Exception:
        _request_metrics["errors"] += 1
        logger.exception("request_id=%s method=%s path=%s unhandled_error", request_id, request.method, path)
        raise
    duration_ms = (time.perf_counter() - started) * 1000
    if response.status_code >= 500:
        _request_metrics["errors"] += 1
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id, request.method, path, response.status_code, duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; media-src 'self' blob:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    if request.url.scheme == "https" and os.getenv("NAHAVIDEO_HSTS", "0") == "1":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

async def _save_upload(file: UploadFile, path: Path, max_bytes: int) -> int:
    total = 0
    with path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                path.unlink(missing_ok=True)
                raise HTTPException(413, f"Upload exceeds the {max_bytes // (1024 * 1024)} MB limit")
            out.write(chunk)
    return total


class PlanRequest(BaseModel):
    prompt: str
    command: str = ""
    duration: int = 30
    clip_ids: list[str]
    music_id: str | None = None
    logo_id: str | None = None
    creative_direction: dict | None = None
    creative_brief: dict | None = None
    stock_asset_ids: list[str] = []


class RenderRequest(BaseModel):
    plan: dict
    clip_ids: list[str]
    music_id: str | None = None
    logo_id: str | None = None
    captions: bool = True
    platform: str = "reels"
    platforms: list[str] = []
    stock_asset_ids: list[str] = []


class BriefRequest(BaseModel):
    url: str
    prompt: str = ""
    command: str = ""


class AssetScoutRequest(BaseModel):
    url: str
    task: str = ""
    requirements: list[str] = []


class CobaltImportRequest(BaseModel):
    url: str
    authorized: bool = False
    video_quality: str = "1080"


class StockScoutRequest(BaseModel):
    gaps: list[dict] = []
    max_missions: int = 6


MEDIA_SUFFIXES = {
    ".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv",
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
    ".png", ".jpg", ".jpeg", ".webp",
}


def _find_media(mid: str):
    matches = [
        path for path in MEDIA.glob(f"{mid}.*")
        if path.suffix.lower() in MEDIA_SUFFIXES
    ]
    return matches[0] if matches else None


class ProjectRequest(BaseModel):
    id: str = ""
    name: str = ""
    prompt: str = ""
    plan: dict
    clip_ids: list[str] = []
    stock_asset_ids: list[str] = []
    music_id: str | None = None
    logo_id: str | None = None
    platforms: list[str] = []
    clips: list[dict] = []
    stock_assets: list[dict] = []
    creative_brief: dict | None = None
    creative_direction: dict | None = None
    command: str = ""


@app.get("/api/auth/status")
def auth_status(request: Request):
    return {"required": auth_enabled(), "authenticated": valid_session(request.cookies.get("nahavideo_session"))}


class LoginRequest(BaseModel):
    password: str


@app.post("/api/login")
def login(req: LoginRequest, request: Request):
    if not auth_enabled():
        return {"required": False, "authenticated": True}
    token = issue_session(req.password)
    if not token:
        raise HTTPException(401, "Invalid password")
    response = JSONResponse({"required": True, "authenticated": True})
    response.set_cookie("nahavideo_session", token, **cookie_options(request))
    return response


@app.post("/api/logout")
def logout():
    response = JSONResponse({"authenticated": False})
    response.delete_cookie("nahavideo_session", path="/")
    return response

@app.get("/api/ready")
def ready():
    checks = {
        "media_dir": MEDIA.exists() and os.access(MEDIA, os.W_OK),
        "project_dir": PROJECTS.exists() and os.access(PROJECTS, os.W_OK),
        "ffmpeg": bool(_shutil.which("ffmpeg")),
    }
    ready_state = all(checks.values())
    return JSONResponse(
        {"ready": ready_state, "checks": checks, "version": app.version},
        status_code=200 if ready_state else 503,
    )


@app.get("/api/runtime")
def runtime_status():
    total, used, free = _shutil.disk_usage(DATA_ROOT)
    return {
        "version": app.version,
        "data_root": str(DATA_ROOT),
        "disk": {"total_bytes": total, "used_bytes": used, "free_bytes": free},
        "limits": {
            "video_mb": MAX_VIDEO_UPLOAD_BYTES // (1024 * 1024),
            "stock_mb": MAX_STOCK_UPLOAD_BYTES // (1024 * 1024),
            "audio_mb": MAX_AUDIO_UPLOAD_BYTES // (1024 * 1024),
            "logo_mb": MAX_LOGO_UPLOAD_BYTES // (1024 * 1024),
        },
        "rate_limit_per_minute": RATE_LIMIT_PER_MINUTE,
    }


@app.get("/api/projects")
def get_projects():
    return {"projects": list_projects(PROJECTS)}


@app.post("/api/projects")
def create_project(req: ProjectRequest):
    payload = req.model_dump()
    payload["id"] = normalize_project_id(
        payload.get("id") or payload.get("name") or "project-" + uuid4().hex[:8]
    )
    payload["name"] = payload.get("name") or payload["id"]
    document = save_project(PROJECTS, payload)
    return {"status": "saved", "project": document}


@app.get("/api/projects/{project_id}")
def get_project(project_id: str):
    try:
        return load_project(PROJECTS, project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    except json.JSONDecodeError:
        raise HTTPException(500, "Saved project is invalid")


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "product": "NahaVideo AI Director",
        "version": "0.43.0",
        "motion_engine": "injected-or-ffmpeg-fallback",
        "stock_ingestion": "provenance-aware-upload",
        "cobalt": {
            "enabled": cobalt_configured(),
            "mode": "self-hosted-only",
        },
        "ffmpeg_skill": "available" if ffmpeg_skill_available() else "native-ffmpeg-fallback",
        "delivery_pack": "ready",
        "nahallm": {
            "enabled": NahaLLMClient().enabled,
            "configured": NahaLLMClient().configured,
        },
        "jev": {
            "enabled": JevBrowserAgent().enabled,
            "configured": JevBrowserAgent().configured,
        },
    }


@app.post("/api/brief-from-url")
def brief_from_url(req: BriefRequest):
    try:
        site = fetch_brand(validate_public_url(req.url, label="website URL"))
        creative = compile_creative_brief(site, req.prompt)
        creative["shot_requirements"] = shot_requirements(creative)
        naha_context = compile_context(req.command, req.prompt, creative)
        creative["naha_context"] = naha_context
        creative["direction"] = creative_direction(creative, req.prompt, naha_context)
        if NahaLLMClient().enabled or JevBrowserAgent().enabled:
            safe_url = validate_public_url(req.url, label="website URL")
            creative["asset_scout"] = scout_website_assets(
                safe_url,
                req.prompt,
                metadata={"command": req.command, "automatic": True},
            )
            if creative["asset_scout"].get("assets"):
                creative["asset_scout"]["collected_assets"] = collect_public_assets(
                    creative["asset_scout"]["assets"],
                    source_url=safe_url,
                )
        return {"site": site, "creative_brief": creative, "naha_context": naha_context}
    except Exception as e:
        raise HTTPException(400, f"Website intake failed: {e}")


@app.post("/api/asset-scout")
def asset_scout(req: AssetScoutRequest):
    if not NahaLLMClient().enabled and not JevBrowserAgent().enabled:
        return {
            "status": "disabled",
            "message": "Enable NahaLLM and/or Jev to run the browser asset scout.",
        }
    try:
        safe_url = validate_public_url(req.url, label="website URL")
        result = scout_website_assets(
            safe_url,
            req.task,
            metadata={"requirements": req.requirements, "manual": True},
        )
        if result.get("assets"):
            result["collected_assets"] = collect_public_assets(
                result["assets"],
                source_url=req.url,
            )
        return result
    except Exception as exc:
        raise HTTPException(400, f"Asset scout failed: {type(exc).__name__}: {exc}")


@app.post("/api/cobalt/ingest")
def cobalt_ingest(req: CobaltImportRequest):
    if not req.authorized:
        raise HTTPException(400, "Confirm you are authorized to download and reuse this media")
    if not cobalt_configured():
        raise HTTPException(400, "Cobalt is not configured")
    try:
        safe_source_url = validate_public_url(req.url, label="media URL")
        response = request_media(safe_source_url, video_quality=req.video_quality)
        candidates = normalize_candidates(safe_source_url, response)
        imported = []
        for candidate in candidates[:6]:
            media_url = str(candidate.get("url") or "")
            if not media_url or not candidate_download_allowed(media_url):
                continue
            try:
                import urllib.request as _ur
                from urllib.parse import urlparse as _urlparse
                suffix = Path(_urlparse(media_url).path).suffix.lower()
                if suffix not in {".mp4", ".webm", ".mov", ".m4v"}:
                    suffix = ".mp4"
                sid = uuid4().hex[:12]
                path = MEDIA / f"{sid}{suffix}"
                request = _ur.Request(media_url, headers={"User-Agent": "NahaVideo/0.25 (+cobalt-import)"})
                with _ur.urlopen(request, timeout=30) as stream, path.open("wb") as out:
                    total = 0
                    while True:
                        chunk = stream.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > 80 * 1024 * 1024:
                            raise ValueError("Cobalt media exceeds the 80 MB import limit")
                        out.write(chunk)
                meta = ffprobe(path)
                provenance = register_stock_asset(
                    path,
                    beat="imported",
                    intent="result",
                    provider="cobalt",
                    source_url=safe_source_url,
                    license_name="operator-confirmed",
                    attribution="",
                    approved=False,
                )
                analysis = enrich_analysis_with_stock(analyze_media(path), path)
                imported.append(stock_public(sid, candidate.get("filename") or path.name, path, meta, analysis))
            except Exception:
                try:
                    path.unlink(missing_ok=True)
                    path.with_suffix(path.suffix + ".stock.json").unlink(missing_ok=True)
                except Exception:
                    pass
        return {"status": "imported" if imported else "no_importable_media", "source_url": req.url, "assets": imported}
    except CobaltError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/cobalt/import")
def cobalt_import(req: CobaltImportRequest):
    if not req.authorized:
        raise HTTPException(400, "Confirm you are authorized to download and reuse this media")
    if not cobalt_configured():
        return {
            "status": "disabled",
            "message": "Cobalt is not configured. Set NAHAVIDEO_COBALT_API_URL to your self-hosted Cobalt instance.",
            "candidates": [],
        }
    try:
        response = request_media(req.url, video_quality=req.video_quality)
        candidates = normalize_candidates(req.url, response)
        return {
            "status": "candidates" if candidates else "no_media",
            "provider": "cobalt",
            "source_url": req.url,
            "cobalt_status": response.get("status"),
            "candidates": candidates,
            "note": "Review the returned media and import only content you are authorized to use.",
        }
    except CobaltError as exc:
        raise HTTPException(400, str(exc))


@app.post("/api/stock-scout")
def stock_scout(req: StockScoutRequest):
    if not JevBrowserAgent().enabled:
        return {
            "status": "disabled",
            "message": "Enable Jev to automatically search stock providers for missing footage.",
        }
    try:
        return scout_missing_stock(req.gaps, max_missions=req.max_missions)
    except Exception as exc:
        raise HTTPException(400, f"Stock scout failed: {type(exc).__name__}: {exc}")



@app.get("/api/assets/{asset_id}")
def get_asset(asset_id: str):
    path = _find_media(asset_id)
    if not path:
        raise HTTPException(404, "Asset not found")
    return FileResponse(path)


@app.post("/api/assets/{asset_id}/approve")
def approve_asset(asset_id: str):
    path = _find_media(asset_id)
    if not path:
        raise HTTPException(404, "Asset not found")
    stock = (enrich_analysis_with_stock({}, path).get("stock") or {})
    if stock.get("kind") != "stock":
        raise HTTPException(400, "Only stock assets can be approved here")
    stock["approved"] = True
    stock["provenance_status"] = "approved_by_operator"
    path.with_suffix(path.suffix + ".stock.json").write_text(
        __import__("json").dumps(stock, indent=2),
        encoding="utf-8",
    )
    return {"id": asset_id, **stock}


@app.post("/api/upload")
async def upload(files: list[UploadFile] = File(...)):
    results = []
    allowed = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
    for f in files:
        suffix = Path(f.filename or "").suffix.lower()
        if suffix not in allowed:
            raise HTTPException(400, f"Unsupported video type: {suffix}")
        cid = uuid4().hex[:12]
        path = MEDIA / f"{cid}{suffix}"
        await _save_upload(f, path, MAX_VIDEO_UPLOAD_BYTES)
        try:
            meta = ffprobe(path)
            analysis = analyze_media(path)
        except Exception as e:
            path.unlink(missing_ok=True)
            raise HTTPException(400, str(e))
        results.append({
            "id": cid, "filename": f.filename, "path": str(path),
            **meta, "analysis": analysis
        })
    return results


@app.post("/api/upload-stock")
async def upload_stock(
    file: UploadFile = File(...),
    beat: str = Form(""),
    intent: str = Form("cta"),
    provider: str = Form(""),
    source_url: str = Form(""),
    license_name: str = Form(""),
    attribution: str = Form(""),
    approved: bool = Form(False),
):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}:
        raise HTTPException(400, f"Unsupported stock video type: {suffix}")
    sid = uuid4().hex[:12]
    path = MEDIA / f"{sid}{suffix}"
    await _save_upload(file, path, MAX_STOCK_UPLOAD_BYTES)
    try:
        meta = ffprobe(path)
        register_stock_asset(
            path,
            beat=beat or intent,
            intent=intent,
            provider=provider,
            source_url=source_url,
            license_name=license_name,
            attribution=attribution,
            approved=approved,
        )
        analysis = enrich_analysis_with_stock(analyze_media(path), path)
    except Exception as e:
        path.unlink(missing_ok=True)
        path.with_suffix(path.suffix + ".stock.json").unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    return stock_public(sid, file.filename or path.name, path, meta, analysis)


@app.post("/api/upload-music")
async def upload_music(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}:
        raise HTTPException(400, f"Unsupported music type: {suffix}")
    mid = uuid4().hex[:12]
    path = MEDIA / f"{mid}{suffix}"
    await _save_upload(file, path, MAX_AUDIO_UPLOAD_BYTES)
    try:
        meta = ffprobe(path)
    except Exception as e:
        path.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    return {"id": mid, "filename": file.filename, "duration": meta["duration"]}


@app.post("/api/upload-logo")
async def upload_logo(file: UploadFile = File(...)):
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(400, "Logo must be PNG, JPG or WebP")
    lid = uuid4().hex[:12]
    path = MEDIA / f"{lid}{suffix}"
    await _save_upload(file, path, MAX_LOGO_UPLOAD_BYTES)
    return {"id": lid, "filename": file.filename}


@app.post("/api/plan")
def plan(req: PlanRequest):
    requested_ids = list(dict.fromkeys(req.clip_ids + req.stock_asset_ids))
    clips = []
    for cid in requested_ids:
        path = _find_media(cid)
        if not path:
            raise HTTPException(404, f"Clip not found: {cid}")
        meta = ffprobe(path)
        analysis = enrich_analysis_with_stock(analyze_media(path), path)
        clips.append(Clip(
            cid, path.name, str(path), meta["duration"], meta["width"],
            meta["height"], meta["fps"], analysis
        ))
    naha_context = compile_context(req.command, req.prompt, req.creative_brief)
    direction = req.creative_direction or creative_direction(req.creative_brief or {}, req.prompt, naha_context)
    result = build_plan(clips, req.prompt, req.duration, direction, naha_context)
    result["naha_context"] = naha_context
    result["storyboard"] = build_storyboard(result)
    result = add_transcript_captions(result)
    result["edit_rationale"] = build_edit_rationale(result)
    music_path = _find_media(req.music_id) if req.music_id else None
    result["audio"]["background_music"] = bool(music_path)
    if music_path:
        beat_info = detect_beats(music_path)
        result["audio"]["music_beats"] = beat_info
        if beat_info.get("beat_times"):
            result["timeline"], pacing_decisions = align_cut_boundaries(
                result["timeline"],
                beat_info["beat_times"],
                total_duration=float(req.duration),
                tolerance=0.28,
            )
            result["pacing_decisions"] = pacing_decisions
            result = sanitize_plan(result, set(requested_ids), float(req.duration))
        else:
            result["pacing_decisions"] = []
    else:
        result["audio"]["music_beats"] = {"available": False, "beat_times": [], "bpm": None, "reason": "no background music"}
        result["pacing_decisions"] = []
    result["audio"]["music_id"] = req.music_id
    result["branding"]["logo_id"] = req.logo_id if req.logo_id and _find_media(req.logo_id) else None
    brief = req.creative_brief or {"category": result["settings"].get("priority") == "food" and "restaurant" or "business"}
    brief["shot_requirements"] = brief.get("shot_requirements") or shot_requirements(brief)
    result["footage_gaps"] = detect_footage_gaps(
        brief, direction, result["timeline"],
        [{"filename": c.filename, "analysis": c.analysis or {}} for c in clips],
    )
    result["stock_manifest"] = build_stock_manifest(result["footage_gaps"].get("gaps", []))
    result["stock_assets"] = [
        {
            "id": c.id,
            "filename": c.filename,
            **((c.analysis or {}).get("stock") or {}),
        }
        for c in clips
        if ((c.analysis or {}).get("stock") or {}).get("kind") == "stock"
    ]
    return result


@app.post("/api/final-qa")
def final_qa(req: RenderRequest):
    requested_ids = list(dict.fromkeys(req.clip_ids + req.stock_asset_ids))
    clips = {cid: _find_media(cid) for cid in requested_ids}
    clips = {k: v for k, v in clips.items() if v}
    approved = set(req.stock_asset_ids)
    return validate_final_plan(req.plan, clips, approved_stock_ids=approved)


@app.post("/api/delivery-manifest")
def delivery_manifest(req: RenderRequest):
    requested_ids = list(dict.fromkeys(req.clip_ids + req.stock_asset_ids))
    clips = {cid: _find_media(cid) for cid in requested_ids}
    clips = {k: v for k, v in clips.items() if v}
    qa = validate_final_plan(req.plan, clips, approved_stock_ids=set(req.stock_asset_ids))
    return build_delivery_manifest(
        req.plan, clips, qa=qa,
        platforms=req.platforms or [req.platform],
        music_id=req.music_id, logo_id=req.logo_id,
    )


@app.post("/api/variants")
def variants(req: RenderRequest):
    requested_ids = list(dict.fromkeys(req.clip_ids + req.stock_asset_ids))
    clips = {cid: _find_media(cid) for cid in requested_ids}
    clips = {k: v for k, v in clips.items() if v}
    if not clips:
        raise HTTPException(404, "No clips found")
    qa = validate_final_plan(req.plan, clips, approved_stock_ids=set(req.stock_asset_ids))
    if qa.get("status") == "blocked":
        raise HTTPException(400, {"message": "Final QA blocks variant rendering", "qa": qa})
    music = _find_media(req.music_id) if req.music_id else None
    logo = _find_media(req.logo_id) if req.logo_id else None
    clean_plan = sanitize_plan(req.plan, set(clips.keys()), float(req.plan.get("settings", {}).get("duration", 180)))
    clean_plan["storyboard"] = build_storyboard(clean_plan)
    clean_plan = add_transcript_captions(clean_plan)
    rid = uuid4().hex[:12]
    base = MEDIA / f"nahavideo_variants_base_{rid}.mp4"
    try:
        render(MEDIA, clean_plan, clips, base, music, logo, captions=False)
    except Exception as exc:
        raise HTTPException(500, str(exc))
    result = render_variants(base, MEDIA / f"variants_{rid}", ["9:16", "1:1", "16:9"], timeline=clean_plan.get("timeline", []), captions=clean_plan.get("captions", []) )
    return {"id": rid, "qa": qa, "variants": result, "base_download": f"/api/variants/{rid}/base"}

@app.post("/api/render")
def render_video(req: RenderRequest):
    _request_metrics["renders"] += 1
    requested_ids = list(dict.fromkeys(req.clip_ids + req.stock_asset_ids))
    clips = {cid: _find_media(cid) for cid in requested_ids}
    clips = {k: v for k, v in clips.items() if v}
    if not clips:
        raise HTTPException(404, "No clips found")
    music = _find_media(req.music_id) if req.music_id else None
    logo = _find_media(req.logo_id) if req.logo_id else None
    clean_plan = sanitize_plan(
        req.plan,
        set(clips.keys()),
        float(req.plan.get("settings", {}).get("duration", 180))
    )
    clean_plan["storyboard"] = build_storyboard(clean_plan)
    clean_plan = add_transcript_captions(clean_plan)
    rid = uuid4().hex[:12]
    output = MEDIA / f"nahavideo_{rid}.mp4"
    try:
        render(MEDIA, clean_plan, clips, output, music, logo, captions=req.captions)
    except Exception as e:
        raise HTTPException(500, str(e))
    requested_platforms = normalize_platforms(req.platforms or [req.platform])
    delivery_qc = verify_output(output, req.platform)
    delivery_pack = build_delivery_pack(requested_platforms)
    if len(requested_platforms) > 1:
        delivery_pack["note"] = "Base render is complete; use /api/render-pack to generate all requested platform outputs."
    return {
        "id": rid,
        "download": f"/api/render/{rid}",
        "plan": clean_plan,
        "delivery_qc": delivery_qc,
        "delivery_pack": delivery_pack,
    }


@app.post("/api/render-pack")
def render_pack(req: RenderRequest):
    _request_metrics["renders"] += 1
    requested_ids = list(dict.fromkeys(req.clip_ids + req.stock_asset_ids))
    clips = {cid: _find_media(cid) for cid in requested_ids}
    clips = {k: v for k, v in clips.items() if v}
    if not clips:
        raise HTTPException(404, "No clips found")
    music = _find_media(req.music_id) if req.music_id else None
    logo = _find_media(req.logo_id) if req.logo_id else None
    clean_plan = sanitize_plan(
        req.plan,
        set(clips.keys()),
        float(req.plan.get("settings", {}).get("duration", 180))
    )
    clean_plan["storyboard"] = build_storyboard(clean_plan)
    clean_plan = add_transcript_captions(clean_plan)
    rid = uuid4().hex[:12]
    base_output = MEDIA / f"nahavideo_pack_base_{rid}.mp4"
    try:
        render(MEDIA, clean_plan, clips, base_output, music, logo, captions=req.captions)
    except Exception as e:
        raise HTTPException(500, str(e))
    platforms = normalize_platforms(req.platforms or [req.platform])
    pack_dir = MEDIA / f"delivery_{rid}"
    pack = render_delivery_pack(base_output, pack_dir, platforms)
    base_qc = verify_output(base_output, platforms[0])
    return {
        "id": rid,
        "base_download": f"/api/render-pack/{rid}/base",
        "plan": clean_plan,
        "platforms": platforms,
        "base_qc": base_qc,
        "delivery_pack": pack,
    }


@app.get("/api/render-pack/{rid}/base")
def download_pack_base(rid: str):
    path = MEDIA / f"nahavideo_pack_base_{rid}.mp4"
    if not path.exists():
        raise HTTPException(404, "Base render not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/render-pack/{rid}/{platform}")
def download_pack_platform(rid: str, platform: str):
    key = normalize_platforms([platform])[0]
    path = MEDIA / f"delivery_{rid}" / f"nahavideo_pack_base_{rid}_{key}.mp4"
    if not path.exists():
        raise HTTPException(404, "Platform render not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/render/{rid}")
def download_variant_base(rid: str):
    path = MEDIA / f"nahavideo_variants_base_{rid}.mp4"
    if not path.exists():
        raise HTTPException(404, "Variant base render not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/variants/{rid}/{aspect}")
def download_variant(rid: str, aspect: str):
    if aspect not in {"9x16", "1x1", "16x9"}:
        raise HTTPException(400, "Unsupported variant aspect")
    path = MEDIA / f"variants_{rid}" / f"nahavideo_variants_base_{rid}_{aspect}.mp4"
    if not path.exists():
        raise HTTPException(404, "Variant not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.get("/api/render/{rid}")
def download_render(rid: str):
    path = MEDIA / f"nahavideo_{rid}.mp4"
    if not path.exists():
        raise HTTPException(404, "Render not found")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


app.mount("/", StaticFiles(directory=str(ROOT / "app" / "static"), html=True), name="static")
