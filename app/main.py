"""FastAPI application for Thaballei Audio: YouTube Finder, Stem Separator & Remastering Studio."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.audio_studio import (
    EXPORT_FORMATS,
    REMASTER_PRESETS,
    STEM_MODELS,
    AudioStudioManager,
)
from app.video_studio import (
    RESOLUTIONS,
    VideoStudioManager,
    parse_lrc_or_text,
    probe_audio_duration,
)
from app.youtube_service import (
    SUPPORTED_FORMATS,
    DownloadManager,
    delete_cookies_file,
    get_audio_formats,
    get_ffmpeg_path,
    get_youtube_status,
    save_cookies_content,
    search_videos,
    set_configured_browser,
    test_youtube_connection,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
STORAGE_ROOT = Path("/tmp/thaballei") if os.environ.get("VERCEL") else BASE_DIR
DOWNLOADS_DIR = STORAGE_ROOT / "downloads"
STEMS_DIR = STORAGE_ROOT / "stems"
MEDIA_DIR = STORAGE_ROOT / "media"
VIDEOS_DIR = STORAGE_ROOT / "videos"

app = FastAPI(title="Thaballei Audio & Video Studio", version="3.0.0")
download_manager = DownloadManager(download_dir=DOWNLOADS_DIR)
studio_manager = AudioStudioManager(library_dir=DOWNLOADS_DIR, stems_dir=STEMS_DIR)
video_manager = VideoStudioManager(
    media_dir=MEDIA_DIR,
    audio_dir=DOWNLOADS_DIR,
    videos_dir=VIDEOS_DIR,
    studio_manager=studio_manager,
)


class DownloadRequest(BaseModel):
    url: str = Field(..., min_length=5, description="YouTube video URL")
    format: str = Field(default="best", description="Target audio format")
    title: str = Field(default="YouTube Audio", description="Display title")
    save_dir: str | None = Field(default=None, description="Optional custom save directory")


class SeparateRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    model: str = Field(default="htdemucs")


class StemMixRequest(BaseModel):
    stems: list[str] = Field(..., min_length=1)
    gains: dict[str, float] = Field(default_factory=dict)
    output_format: str = Field(default="flac")
    remaster_preset: str | None = Field(default=None)
    output_label: str | None = Field(default=None)
    noise_reduction: float = Field(default=0.0, ge=0, le=100)
    echo_reduction: float = Field(default=0.0, ge=0, le=100)


class RemasterRequest(BaseModel):
    filename: str = Field(..., min_length=1)
    preset: str = Field(default="modern_crisp")
    output_format: str = Field(default="flac")
    clarity: float | None = Field(default=None, ge=0, le=100)
    bass_boost: float | None = Field(default=None, ge=0, le=100)
    stereo_width: float | None = Field(default=None, ge=0, le=100)
    noise_reduction: float | None = Field(default=None, ge=0, le=100)
    echo_reduction: float | None = Field(default=None, ge=0, le=100)
    loudness_norm: bool | None = Field(default=None)


class DawTrackSpec(BaseModel):
    source: str = Field(default="library")  # "library" | "stem"
    filename: str = Field(..., min_length=1)
    stem_set_id: str | None = Field(default=None)
    gain: float = Field(default=1.0, ge=0.0, le=2.0)
    pan: float = Field(default=0.0, ge=-1.0, le=1.0)


class UnifiedRenderRequest(BaseModel):
    tracks: list[DawTrackSpec] = Field(..., min_length=1)
    output_name: str = Field(default="DAW Master")
    output_format: str = Field(default="flac")
    preset: str = Field(default="modern_crisp")
    clarity: float = Field(default=65.0, ge=0, le=100)
    bass_boost: float = Field(default=55.0, ge=0, le=100)
    stereo_width: float = Field(default=35.0, ge=0, le=100)
    compression: float = Field(default=45.0, ge=0, le=100)
    noise_reduction: float = Field(default=0.0, ge=0, le=100)
    echo_reduction: float = Field(default=0.0, ge=0, le=100)
    loudness_norm: bool = Field(default=True)
    master_gain: float = Field(default=1.0, ge=0.0, le=2.0)
    eq_params: dict[str, float] = Field(default_factory=dict)
    save_dir: str | None = Field(default=None)


@app.post("/api/system/pick-folder")
def pick_folder() -> dict[str, str]:
    """Open a native OS folder selection dialog and return the chosen path."""
    code = (
        "import tkinter as tk; from tkinter import filedialog; "
        "root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True); "
        "p = filedialog.askdirectory(title='Choose Save Folder'); print(p or '', end='')"
    )
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    return {"path": proc.stdout.strip()}


@app.get("/api/health")
def health() -> dict[str, Any]:
    """Return service health, FFmpeg availability, and CUDA GPU status."""
    ffmpeg = get_ffmpeg_path()
    cuda_available = False
    gpu_name = None
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception:
        pass
    return {
        "status": "ok",
        "ffmpeg_available": bool(ffmpeg),
        "ffmpeg_path": ffmpeg,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
    }


@app.get("/api/formats")
def list_formats() -> dict[str, Any]:
    """Return supported audio output formats."""
    return {
        "ffmpeg_available": bool(get_ffmpeg_path()),
        "formats": SUPPORTED_FORMATS,
    }


class BrowserCookiesRequest(BaseModel):
    browser: str | None = Field(default=None, description="Browser name to import cookies from (e.g. firefox)")


@app.get("/api/youtube/status")
def youtube_status() -> dict[str, Any]:
    """Return status of YouTube anti-bot protections, active cookies, and JS runtimes."""
    return get_youtube_status()


@app.post("/api/youtube/cookies/browser")
def set_browser_cookies(payload: BrowserCookiesRequest) -> dict[str, Any]:
    """Configure browser to extract cookies from (e.g. 'firefox')."""
    set_configured_browser(payload.browser)
    return get_youtube_status()


@app.post("/api/youtube/cookies/upload")
async def upload_cookies_file(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a Netscape cookies.txt file to authenticate with YouTube."""
    content = await file.read()
    if not content or len(content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Uploaded cookie file is empty.")
    save_cookies_content(content)
    return get_youtube_status()


@app.delete("/api/youtube/cookies")
def clear_cookies() -> dict[str, Any]:
    """Remove active custom cookies.txt and reset browser cookie selection."""
    delete_cookies_file()
    set_configured_browser(None)
    return get_youtube_status()


@app.post("/api/youtube/test")
def test_youtube() -> dict[str, Any]:
    """Verify YouTube connection and ability to search/extract."""
    return test_youtube_connection()


@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1, description="Search query or YouTube URL"),
    limit: int = Query(default=12, ge=1, le=25),
) -> dict[str, Any]:
    """Search YouTube videos or resolve a direct YouTube URL."""
    try:
        results = search_videos(q, limit=limit)
    except Exception as exc:
        err_msg = str(exc)
        if "Sign in to confirm you’re not a bot" in err_msg or "confirm you're not a bot" in err_msg:
            detail = (
                "YouTube requires authentication ('Sign in to confirm you’re not a bot'). "
                "Click 'YT COOKIES' in the top bar to enable Firefox cookies or upload a cookies.txt file."
            )
        else:
            detail = f"YouTube search failed: {exc}"
        raise HTTPException(status_code=502, detail=detail) from exc
    return {"query": q, "count": len(results), "results": results}


@app.get("/api/inspect")
def inspect_video(url: str = Query(..., min_length=5)) -> dict[str, Any]:
    """Inspect available audio streams for a YouTube video."""
    try:
        return get_audio_formats(url)
    except Exception as exc:
        err_msg = str(exc)
        if "Sign in to confirm you’re not a bot" in err_msg or "confirm you're not a bot" in err_msg:
            detail = (
                "YouTube requires authentication ('Sign in to confirm you’re not a bot'). "
                "Click 'YT COOKIES' in the top bar to enable Firefox cookies or upload a cookies.txt file."
            )
        else:
            detail = f"Failed to inspect video: {exc}"
        raise HTTPException(status_code=502, detail=detail) from exc


@app.post("/api/download")
def start_download(payload: DownloadRequest) -> dict[str, Any]:
    """Queue a background audio download job."""
    try:
        job = download_manager.start_download(
            url=payload.url,
            format_choice=payload.format,
            title=payload.title,
            save_dir=payload.save_dir,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@app.get("/api/jobs")
def list_jobs() -> dict[str, Any]:
    """List all download jobs."""
    return {"jobs": download_manager.list_jobs()}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    """Get status for a specific download job."""
    job = download_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {"job": job}


@app.get("/api/files")
def list_files() -> dict[str, Any]:
    """List audio files in the library."""
    return {"files": download_manager.list_files()}


@app.get("/api/files/{filename}")
def get_file(
    filename: str,
    download: bool = Query(default=False, description="Force attachment download"),
) -> FileResponse:
    """Serve or download a saved audio file."""
    try:
        target = download_manager.resolve_file(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc

    if download:
        return FileResponse(path=target, filename=target.name)
    return FileResponse(path=target)


@app.delete("/api/files/{filename}")
def delete_file(filename: str) -> dict[str, str]:
    """Delete a saved audio file."""
    try:
        target = download_manager.resolve_file(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found.") from exc

    target.unlink()
    return {"deleted": target.name}


# --- Audio Studio Endpoints (Upload, Stem Separation, Mixing, Remastering) ---


@app.get("/api/studio/options")
def studio_options() -> dict[str, Any]:
    """Return available stem models, remaster presets, and export formats."""
    return {
        "stem_models": STEM_MODELS,
        "remaster_presets": REMASTER_PRESETS,
        "export_formats": EXPORT_FORMATS,
    }


@app.post("/api/studio/upload")
def upload_audio(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a local audio file into the library for stem separation or remastering."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    safe_name = Path(file.filename).name
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOWNLOADS_DIR / safe_name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"filename": safe_name, "size": dest.stat().st_size}


@app.post("/api/studio/separate")
def separate_stems(payload: SeparateRequest) -> dict[str, Any]:
    """Start a background Demucs stem separation job."""
    if video_manager.has_active_job():
        raise HTTPException(status_code=409, detail="A video render task is currently running.")
    try:
        job = studio_manager.start_separation(payload.filename, model=payload.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@app.get("/api/studio/stems")
def list_stems() -> dict[str, Any]:
    """List all separated stem sets."""
    return {"stem_sets": studio_manager.list_stem_sets()}


@app.get("/api/studio/stems/{stem_set_id}/{stem_filename}")
def get_stem_file(
    stem_set_id: str,
    stem_filename: str,
    download: bool = Query(default=False),
) -> FileResponse:
    """Stream or download an individual separated stem."""
    try:
        target = studio_manager.resolve_stem_file(stem_set_id, stem_filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if download:
        return FileResponse(path=target, filename=f"{stem_set_id}_{target.name}")
    return FileResponse(path=target)


@app.post("/api/studio/stems/{stem_set_id}/mix")
def mix_stems(stem_set_id: str, payload: StemMixRequest) -> dict[str, Any]:
    """Mix selected stems (with optional remastering) and export as a single file."""
    try:
        result = studio_manager.export_stem_mix(
            stem_set_id=stem_set_id,
            stems=payload.stems,
            gains=payload.gains,
            output_format=payload.output_format,
            remaster_preset=payload.remaster_preset,
            output_label=payload.output_label,
            noise_reduction=payload.noise_reduction,
            echo_reduction=payload.echo_reduction,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Mix failed: {exc}") from exc
    return result


@app.post("/api/studio/remaster")
def remaster_audio(payload: RemasterRequest) -> dict[str, Any]:
    """Start a background remastering job on an audio file."""
    try:
        job = studio_manager.start_remaster(
            filename=payload.filename,
            preset=payload.preset,
            output_format=payload.output_format,
            clarity=payload.clarity,
            bass_boost=payload.bass_boost,
            stereo_width=payload.stereo_width,
            noise_reduction=payload.noise_reduction,
            echo_reduction=payload.echo_reduction,
            loudness_norm=payload.loudness_norm,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@app.post("/api/studio/render")
def render_daw_session(payload: UnifiedRenderRequest) -> dict[str, Any]:
    """Render the unified DAW session (tracks + real-time DSP settings) to an audio file."""
    if video_manager.has_active_job():
        raise HTTPException(status_code=409, detail="A video render task is currently running.")
    try:
        job = studio_manager.start_unified_render(
            tracks=[t.model_dump() for t in payload.tracks],
            output_name=payload.output_name,
            output_format=payload.output_format,
            preset=payload.preset,
            clarity=payload.clarity,
            bass_boost=payload.bass_boost,
            stereo_width=payload.stereo_width,
            compression=payload.compression,
            noise_reduction=payload.noise_reduction,
            echo_reduction=payload.echo_reduction,
            loudness_norm=payload.loudness_norm,
            master_gain=payload.master_gain,
            eq_params=payload.eq_params,
            save_dir=payload.save_dir,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@app.get("/api/studio/jobs")
def list_studio_jobs() -> dict[str, Any]:
    """List all stem separation and remastering jobs."""
    return {"jobs": studio_manager.list_jobs()}


@app.get("/api/studio/jobs/{job_id}")
def get_studio_job(job_id: str) -> dict[str, Any]:
    """Get a single studio job's status."""
    job = studio_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Studio job not found.")
    return {"job": job}


# --- Video Studio Endpoints (Photo/GIF/Video + Audio + Animated Lyrics) ---


class ParseLyricsRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    audio_filename: str | None = Field(default=None)


class LyricLine(BaseModel):
    start: float = Field(..., ge=0.0)
    end: float = Field(..., ge=0.0)
    text: str = Field(..., min_length=1)


class RenderVideoRequest(BaseModel):
    media_filename: str = Field(..., min_length=1)
    audio_filename: str = Field(..., min_length=1)
    output_name: str = Field(default="Lyric_Video")
    resolution: str = Field(default="1080p")
    lyrics: list[LyricLine] = Field(default_factory=list)
    font_size: int = Field(default=54, ge=18, le=140)
    text_color: str = Field(default="#FFFFFF")
    outline_color: str = Field(default="#000000")
    position: str = Field(default="bottom")
    fade_in_ms: int = Field(default=350, ge=0, le=2000)
    fade_out_ms: int = Field(default=350, ge=0, le=2000)
    dim_percent: int = Field(default=25, ge=0, le=85)
    title_text: str | None = Field(default=None)
    save_dir: str | None = Field(default=None)


@app.get("/api/video/options")
def video_options() -> dict[str, Any]:
    """Return available video resolutions."""
    return {
        "resolutions": {
            k: {"width": v[0], "height": v[1], "label": v[2]}
            for k, v in RESOLUTIONS.items()
        }
    }


@app.post("/api/video/upload-media")
def upload_video_media(file: UploadFile = File(...)) -> dict[str, Any]:
    """Upload a photo, GIF, or video background for the Video Studio."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename.")
    safe_name = Path(file.filename).name
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    dest = MEDIA_DIR / safe_name
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"filename": safe_name, "size": dest.stat().st_size}


@app.get("/api/video/media")
def list_video_media() -> dict[str, Any]:
    """List uploaded photo/GIF/video backgrounds."""
    return {"media": video_manager.list_media()}


@app.get("/api/video/media/{filename}")
def get_video_media(filename: str) -> FileResponse:
    """Serve an uploaded photo, GIF, or video background."""
    try:
        target = video_manager.resolve_media(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(path=target)


@app.post("/api/video/parse-lyrics")
def parse_lyrics(payload: ParseLyricsRequest) -> dict[str, Any]:
    """Parse LRC timestamps or plain text lines against the selected audio duration."""
    duration = 180.0
    if payload.audio_filename:
        try:
            audio_path = video_manager.resolve_audio(payload.audio_filename)
            duration = probe_audio_duration(audio_path)
        except FileNotFoundError:
            pass
    items = parse_lrc_or_text(payload.raw_text, total_duration=duration)
    return {"lyrics": items, "duration": duration}


@app.post("/api/video/render")
def render_video(payload: RenderVideoRequest) -> dict[str, Any]:
    """Render an MP4 lyric/karaoke video with background media, audio, and fade-animated lyrics."""
    try:
        job = video_manager.start_render_video(
            media_filename=payload.media_filename,
            audio_filename=payload.audio_filename,
            output_name=payload.output_name,
            resolution=payload.resolution,
            lyrics=[line.model_dump() for line in payload.lyrics],
            font_size=payload.font_size,
            text_color=payload.text_color,
            outline_color=payload.outline_color,
            position=payload.position,
            fade_in_ms=payload.fade_in_ms,
            fade_out_ms=payload.fade_out_ms,
            dim_percent=payload.dim_percent,
            title_text=payload.title_text,
            save_dir=payload.save_dir,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"job": job}


@app.get("/api/video/jobs")
def list_video_jobs() -> dict[str, Any]:
    """List video rendering jobs."""
    return {"jobs": video_manager.list_jobs()}


@app.get("/api/video/files")
def list_rendered_videos() -> dict[str, Any]:
    """List rendered MP4 videos."""
    return {"videos": video_manager.list_videos()}


@app.get("/api/video/files/{filename}")
def get_rendered_video(
    filename: str,
    download: bool = Query(default=False),
) -> FileResponse:
    """Stream or download a rendered MP4 video."""
    try:
        target = video_manager.resolve_video(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if download:
        return FileResponse(path=target, filename=target.name)
    return FileResponse(path=target)


@app.delete("/api/video/files/{filename}")
def delete_rendered_video(filename: str) -> dict[str, str]:
    """Delete a rendered MP4 video."""
    try:
        target = video_manager.resolve_video(filename)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    target.unlink()
    return {"deleted": target.name}


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index() -> FileResponse:
    """Serve the web application frontend."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Frontend not found.")
    return FileResponse(path=index_file)
