"""YouTube search, format inspection, and audio download service using yt-dlp."""

from __future__ import annotations

import logging
import os
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yt_dlp

logger = logging.getLogger(__name__)

YOUTUBE_URL_RE = re.compile(
    r"^(https?://)?(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/.+$",
    re.IGNORECASE,
)

SUPPORTED_FORMATS: dict[str, dict[str, str]] = {
    "best": {
        "label": "Best Native (Zero Loss)",
        "description": "Original Opus / M4A stream with no re-encoding",
    },
    "mp3": {
        "label": "MP3 (320 kbps)",
        "description": "Universal compatibility with embedded cover art",
    },
    "flac": {
        "label": "FLAC (Lossless)",
        "description": "Lossless audio container with metadata",
    },
    "m4a": {
        "label": "M4A / AAC",
        "description": "Apple-friendly container with embedded cover art",
    },
    "opus": {
        "label": "Opus",
        "description": "High-efficiency modern audio codec",
    },
    "wav": {
        "label": "WAV (Uncompressed)",
        "description": "Uncompressed PCM audio",
    },
}


def get_ffmpeg_path() -> str | None:
    """Return path to ffmpeg executable, checking PATH then imageio-ffmpeg."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def is_youtube_url(text: str) -> bool:
    """Return True if text looks like a YouTube video or music URL."""
    return bool(YOUTUBE_URL_RE.match(text.strip()))


def format_duration(seconds: int | float | None) -> str:
    """Format duration in seconds to MM:SS or HH:MM:SS."""
    if seconds is None:
        return "Live / Unknown"
    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def _pick_thumbnail(entry: dict[str, Any]) -> str | None:
    if entry.get("thumbnail"):
        return str(entry["thumbnail"])
    thumbnails = entry.get("thumbnails") or []
    if thumbnails:
        best = thumbnails[-1]
        if isinstance(best, dict) and best.get("url"):
            return str(best["url"])
    video_id = entry.get("id")
    if video_id:
        return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
    return None


def _normalize_entry(entry: dict[str, Any]) -> dict[str, Any]:
    video_id = entry.get("id") or ""
    webpage_url = entry.get("webpage_url") or entry.get("url") or ""
    if webpage_url and not webpage_url.startswith("http") and video_id:
        webpage_url = f"https://www.youtube.com/watch?v={video_id}"
    elif not webpage_url and video_id:
        webpage_url = f"https://www.youtube.com/watch?v={video_id}"

    duration = entry.get("duration")
    return {
        "id": video_id,
        "title": entry.get("title") or "Untitled Video",
        "url": webpage_url,
        "channel": entry.get("channel") or entry.get("uploader") or "Unknown channel",
        "duration": duration,
        "duration_text": format_duration(duration),
        "view_count": entry.get("view_count"),
        "thumbnail": _pick_thumbnail(entry),
    }


def search_videos(query: str, limit: int = 12) -> list[dict[str, Any]]:
    """Search YouTube by keyword or resolve a direct YouTube URL."""
    cleaned = query.strip()
    if not cleaned:
        return []

    if is_youtube_url(cleaned):
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(cleaned, download=False)
        if not info:
            return []
        if "entries" in info and info["entries"]:
            return [_normalize_entry(e) for e in info["entries"] if e][:limit]
        return [_normalize_entry(info)]

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    search_expr = f"ytsearch{max(1, min(limit, 25))}:{cleaned}"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_expr, download=False)

    entries = (info or {}).get("entries") or []
    results = []
    for entry in entries:
        if not entry:
            continue
        results.append(_normalize_entry(entry))
    return results


def get_audio_formats(url: str) -> dict[str, Any]:
    """Inspect available audio streams for a YouTube URL."""
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if not info:
        raise ValueError("Could not retrieve video metadata.")

    audio_streams: list[dict[str, Any]] = []
    for fmt in info.get("formats") or []:
        acodec = fmt.get("acodec")
        vcodec = fmt.get("vcodec")
        if not acodec or acodec == "none":
            continue
        is_audio_only = vcodec in (None, "none")
        if not is_audio_only:
            continue
        abr = fmt.get("abr") or fmt.get("tbr") or 0
        audio_streams.append(
            {
                "format_id": fmt.get("format_id"),
                "ext": fmt.get("ext"),
                "acodec": acodec,
                "abr": round(float(abr), 1) if abr else None,
                "asr": fmt.get("asr"),
                "filesize": fmt.get("filesize") or fmt.get("filesize_approx"),
                "format_note": fmt.get("format_note") or "",
            }
        )

    audio_streams.sort(key=lambda item: item.get("abr") or 0, reverse=True)
    return {
        "video": _normalize_entry(info),
        "best_native": audio_streams[0] if audio_streams else None,
        "streams": audio_streams,
    }


@dataclass
class DownloadJob:
    """Tracks state and progress for a single audio download."""

    job_id: str
    url: str
    title: str
    format_choice: str
    status: str = "queued"
    progress: float = 0.0
    speed: str | None = None
    eta: str | None = None
    filename: str | None = None
    filesize: int | None = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DownloadManager:
    """Thread-pooled manager for background yt-dlp audio downloads."""

    def __init__(self, download_dir: Path, max_workers: int = 1) -> None:
        self.download_dir = download_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs]

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job else None

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for key, value in updates.items():
                setattr(job, key, value)

    def start_download(
        self,
        url: str,
        format_choice: str = "best",
        title: str = "YouTube Audio",
        save_dir: str | None = None,
    ) -> dict[str, Any]:
        if format_choice not in SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {format_choice}")

        job_id = uuid.uuid4().hex[:12]
        job = DownloadJob(
            job_id=job_id,
            url=url,
            title=title,
            format_choice=format_choice,
        )
        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._run_download, job_id, url, format_choice, save_dir)
        return job.to_dict()

    def _build_ydl_opts(self, job_id: str, format_choice: str) -> dict[str, Any]:
        ffmpeg_path = get_ffmpeg_path()
        outtmpl = str(self.download_dir / "%(title).160B [%(id)s].%(ext)s")

        def progress_hook(d: dict[str, Any]) -> None:
            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                pct = round((downloaded / total) * 100, 1) if total else 0.0
                self._update_job(
                    job_id,
                    status="downloading",
                    progress=min(pct, 99.9),
                    speed=d.get("_speed_str", "").strip() or None,
                    eta=d.get("_eta_str", "").strip() or None,
                )
            elif status == "finished":
                self._update_job(
                    job_id,
                    status="processing",
                    progress=99.0,
                    speed=None,
                    eta=None,
                )

        def postprocessor_hook(d: dict[str, Any]) -> None:
            if d.get("status") == "finished":
                info = d.get("info_dict") or {}
                filepath = info.get("filepath") or d.get("filepath")
                if filepath and os.path.exists(filepath):
                    self._update_job(
                        job_id,
                        filename=Path(filepath).name,
                        filesize=os.path.getsize(filepath),
                    )

        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "outtmpl": outtmpl,
            "restrictfilenames": False,
            "windowsfilenames": True,
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [postprocessor_hook],
        }

        if ffmpeg_path:
            opts["ffmpeg_location"] = ffmpeg_path

        postprocessors: list[dict[str, Any]] = []

        if format_choice == "best":
            opts["format"] = "bestaudio/best"
            if ffmpeg_path:
                postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})
        elif format_choice == "mp3":
            if not ffmpeg_path:
                raise RuntimeError("FFmpeg is required to convert audio to MP3.")
            opts["format"] = "bestaudio/best"
            opts["writethumbnail"] = True
            postprocessors.extend(
                [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "320",
                    },
                    {"key": "FFmpegMetadata", "add_metadata": True},
                    {"key": "EmbedThumbnail"},
                ]
            )
        elif format_choice == "flac":
            if not ffmpeg_path:
                raise RuntimeError("FFmpeg is required to convert audio to FLAC.")
            opts["format"] = "bestaudio/best"
            opts["writethumbnail"] = True
            postprocessors.extend(
                [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "flac",
                    },
                    {"key": "FFmpegMetadata", "add_metadata": True},
                    {"key": "EmbedThumbnail"},
                ]
            )
        elif format_choice == "m4a":
            if not ffmpeg_path:
                raise RuntimeError("FFmpeg is required to convert audio to M4A.")
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
            opts["writethumbnail"] = True
            postprocessors.extend(
                [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "m4a",
                        "preferredquality": "0",
                    },
                    {"key": "FFmpegMetadata", "add_metadata": True},
                    {"key": "EmbedThumbnail"},
                ]
            )
        elif format_choice == "opus":
            if not ffmpeg_path:
                raise RuntimeError("FFmpeg is required to extract Opus audio.")
            opts["format"] = "bestaudio[acodec=opus]/bestaudio/best"
            postprocessors.extend(
                [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "opus",
                    },
                    {"key": "FFmpegMetadata", "add_metadata": True},
                ]
            )
        elif format_choice == "wav":
            if not ffmpeg_path:
                raise RuntimeError("FFmpeg is required to convert audio to WAV.")
            opts["format"] = "bestaudio/best"
            postprocessors.extend(
                [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "wav",
                    },
                    {"key": "FFmpegMetadata", "add_metadata": True},
                ]
            )

        if postprocessors:
            opts["postprocessors"] = postprocessors

        return opts

    def _run_download(
        self, job_id: str, url: str, format_choice: str, save_dir: str | None = None
    ) -> None:
        try:
            self._update_job(job_id, status="downloading", progress=0.0)
            opts = self._build_ydl_opts(job_id, format_choice)

            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)

            resolved_title = (info or {}).get("title")
            final_path: Path | None = None

            requested_downloads = (info or {}).get("requested_downloads") or []
            for req in requested_downloads:
                fp = req.get("filepath")
                if fp and os.path.exists(fp):
                    final_path = Path(fp)
                    break

            if not final_path and info:
                prepared = Path(ydl.prepare_filename(info))
                if prepared.exists():
                    final_path = prepared
                elif format_choice != "best":
                    alt = prepared.with_suffix(f".{format_choice}")
                    if alt.exists():
                        final_path = alt

            # Clean up leftover thumbnail files if any remained
            if final_path:
                stem = final_path.stem
                for thumb_ext in (".webp", ".jpg", ".jpeg", ".png"):
                    thumb_candidate = self.download_dir / f"{stem}{thumb_ext}"
                    if thumb_candidate.exists():
                        try:
                            thumb_candidate.unlink()
                        except OSError:
                            pass

            updates: dict[str, Any] = {
                "status": "completed",
                "progress": 100.0,
                "speed": None,
                "eta": None,
            }
            if resolved_title:
                updates["title"] = resolved_title
            if final_path and final_path.exists():
                updates["filename"] = final_path.name
                updates["filesize"] = final_path.stat().st_size
                if save_dir and save_dir.strip():
                    dest_dir = Path(save_dir.strip())
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(final_path, dest_dir / final_path.name)

            self._update_job(job_id, **updates)
        except Exception as exc:
            logger.exception("Download job %s failed", job_id)
            self._update_job(
                job_id,
                status="error",
                error=str(exc),
                speed=None,
                eta=None,
            )

    def list_files(self) -> list[dict[str, Any]]:
        """List downloaded audio files in download_dir."""
        if not self.download_dir.exists():
            return []
        files = []
        for path in self.download_dir.iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() in {".part", ".ytdl", ".temp"}:
                continue
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "ext": path.suffix.lstrip(".").lower(),
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        files.sort(key=lambda f: f["modified_at"], reverse=True)
        return files

    def resolve_file(self, filename: str) -> Path:
        """Safely resolve a file inside download_dir preventing path traversal."""
        safe_name = Path(filename).name
        target = (self.download_dir / safe_name).resolve()
        root = self.download_dir.resolve()
        if target.parent != root or not target.is_file():
            raise FileNotFoundError("File not found.")
        return target
