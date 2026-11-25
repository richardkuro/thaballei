"""Video Studio service: photo/GIF/video background + audio + animated ASS lyrics."""

from __future__ import annotations

import logging
import re
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.youtube_service import get_ffmpeg_path

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
GIF_EXTS = {".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".avi"}
MEDIA_EXTS = IMAGE_EXTS | GIF_EXTS | VIDEO_EXTS

RESOLUTIONS: dict[str, tuple[int, int, str]] = {
    "1080p": (1920, 1080, "1080p Landscape (16:9)"),
    "720p": (1280, 720, "720p HD Landscape (16:9)"),
    "shorts": (1080, 1920, "1080x1920 Vertical (9:16)"),
    "square": (1080, 1080, "1080x1080 Square (1:1)"),
}


def _safe_slug(name: str) -> str:
    stem = Path(name).stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    return cleaned[:80] or "video"


def _hex_to_ass_color(hex_color: str, alpha: int = 0) -> str:
    """Convert #RRGGBB to ASS &HAABBGGRR color format."""
    cleaned = hex_color.strip().lstrip("#")
    if len(cleaned) != 6:
        cleaned = "FFFFFF"
    r = cleaned[0:2]
    g = cleaned[2:4]
    b = cleaned[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _format_ass_time(seconds: float) -> str:
    """Format seconds into H:MM:SS.cs (centiseconds) for ASS subtitles."""
    s = max(0.0, float(seconds))
    hours = int(s // 3600)
    minutes = int((s % 3600) // 60)
    secs = s % 60.0
    whole_secs = int(secs)
    cs = int(round((secs - whole_secs) * 100))
    if cs >= 100:
        cs = 99
    return f"{hours}:{minutes:02d}:{whole_secs:02d}.{cs:02d}"


def parse_lrc_or_text(raw_text: str, total_duration: float = 180.0) -> list[dict[str, Any]]:
    """Parse [mm:ss.xx] LRC timestamps or plain lines into timed lyric items."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if not lines:
        return []

    lrc_re = re.compile(r"^\[(\d{1,2}):(\d{2})(?:\.(\d{1,3}))?\]\s*(.*)$")
    parsed_lrc: list[tuple[float, str]] = []
    for line in lines:
        m = lrc_re.match(line)
        if m:
            mins = int(m.group(1))
            secs = int(m.group(2))
            frac_str = m.group(3) or "0"
            frac = int(frac_str) / (10 ** len(frac_str))
            text = m.group(4).strip()
            if text:
                parsed_lrc.append((mins * 60 + secs + frac, text))

    if parsed_lrc:
        parsed_lrc.sort(key=lambda x: x[0])
        items: list[dict[str, Any]] = []
        for idx, (start, text) in enumerate(parsed_lrc):
            if idx + 1 < len(parsed_lrc):
                end = max(start + 0.8, parsed_lrc[idx + 1][0] - 0.1)
            else:
                end = max(start + 3.0, min(total_duration, start + 5.0))
            items.append({"start": round(start, 2), "end": round(end, 2), "text": text})
        return items

    # Plain text fallback: distribute evenly across audio duration
    dur = max(10.0, float(total_duration))
    step = dur / len(lines)
    items = []
    for idx, text in enumerate(lines):
        start = round(idx * step, 2)
        end = round(min(dur, (idx + 1) * step - 0.1), 2)
        if end <= start:
            end = round(start + 1.0, 2)
        items.append({"start": start, "end": end, "text": text})
    return items


def build_ass_subtitles(
    lyrics: list[dict[str, Any]],
    width: int,
    height: int,
    font_size: int = 54,
    text_color: str = "#FFFFFF",
    outline_color: str = "#000000",
    position: str = "bottom",
    fade_in_ms: int = 350,
    fade_out_ms: int = 350,
    title_text: str | None = None,
) -> str:
    """Generate an ASS subtitle script with smooth \\fad(in, out) animations."""
    alignment = {"bottom": 2, "center": 5, "top": 8}.get(position, 2)
    margin_v = int(height * 0.08) if position != "center" else 0
    primary = _hex_to_ass_color(text_color, 0)
    outline = _hex_to_ass_color(outline_color, 0)
    shadow = _hex_to_ass_color("#000000", 90)

    header = "\n".join(
        [
            "[Script Info]",
            "ScriptType: v4.00+",
            f"PlayResX: {width}",
            f"PlayResY: {height}",
            "ScaledBorderAndShadow: yes",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Lyric,Arial,{font_size},{primary},{primary},{outline},{shadow},-1,0,0,0,100,100,1,0,1,3,2,{alignment},40,40,{margin_v},1",
            f"Style: Title,Arial,{max(28, int(font_size * 0.65))},{primary},{primary},{outline},{shadow},-1,0,0,0,100,100,2,0,1,2,1,8,40,40,{int(height * 0.05)},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        ]
    )

    events: list[str] = []
    if title_text and title_text.strip():
        safe_title = title_text.strip().replace("\n", "\\N")
        events.append(
            f"Dialogue: 1,0:00:00.20,0:00:05.00,Title,,0,0,0,,{{\\fad(400,600)}}{safe_title}"
        )

    fin = max(0, int(fade_in_ms))
    fout = max(0, int(fade_out_ms))
    # Enforce strictly sequential, non-overlapping lyrics
    ordered = sorted(
        [item for item in lyrics if str(item.get("text") or "").strip()],
        key=lambda x: float(x.get("start", 0.0)),
    )
    prev_end = 0.0
    for idx, item in enumerate(ordered):
        text = str(item.get("text") or "").strip()
        start = max(prev_end, float(item.get("start", 0.0)))
        end = max(start + 0.3, float(item.get("end", start + 2.0)))
        if idx + 1 < len(ordered):
            next_start = float(ordered[idx + 1].get("start", end))
            if end > next_start and next_start > start + 0.3:
                end = round(next_start - 0.02, 2)
        prev_end = end
        escaped = text.replace("\r\n", "\n").replace("\n", "\\N")
        events.append(
            f"Dialogue: 0,{_format_ass_time(start)},{_format_ass_time(end)},Lyric,,0,0,0,,{{\\fad({fin},{fout})}}{escaped}"
        )

    return header + "\n" + "\n".join(events) + "\n"


def probe_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds using FFmpeg."""
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        return 180.0
    proc = subprocess.run(
        [ffmpeg, "-i", str(audio_path)],
        capture_output=True,
        text=True,
    )
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr or "")
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return 180.0


def _escape_ffmpeg_filter_path(path: Path) -> str:
    """Escape a Windows path for FFmpeg's ass= filter."""
    s = str(path.resolve()).replace("\\", "/")
    s = s.replace(":", "\\:")
    return f"'{s}'"


@dataclass
class VideoJob:
    job_id: str
    title: str
    status: str = "queued"
    progress: float = 0.0
    detail: str | None = None
    output_filename: str | None = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VideoStudioManager:
    """Manages media backgrounds and FFmpeg lyric/karaoke video rendering."""

    def __init__(
        self,
        media_dir: Path,
        audio_dir: Path,
        videos_dir: Path,
        studio_manager: Any = None,
    ) -> None:
        self.media_dir = media_dir
        self.audio_dir = audio_dir
        self.videos_dir = videos_dir
        self.studio_manager = studio_manager
        self.media_dir.mkdir(parents=True, exist_ok=True)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._jobs: dict[str, VideoJob] = {}
        self._lock = threading.Lock()

    def has_active_job(self) -> bool:
        with self._lock:
            return any(j.status in ("queued", "processing") for j in self._jobs.values())

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            jobs = list(self._jobs.values())
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in jobs]

    def _update_job(self, job_id: str, **updates: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in updates.items():
                setattr(job, k, v)

    def list_media(self) -> list[dict[str, Any]]:
        items = []
        for p in self.media_dir.iterdir():
            if not p.is_file() or p.suffix.lower() not in MEDIA_EXTS:
                continue
            ext = p.suffix.lower()
            kind = "image" if ext in IMAGE_EXTS else "gif" if ext in GIF_EXTS else "video"
            stat = p.stat()
            items.append(
                {
                    "name": p.name,
                    "kind": kind,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        items.sort(key=lambda x: x["modified_at"], reverse=True)
        return items

    def list_videos(self) -> list[dict[str, Any]]:
        items = []
        for p in self.videos_dir.iterdir():
            if not p.is_file() or p.suffix.lower() != ".mp4":
                continue
            stat = p.stat()
            items.append(
                {
                    "name": p.name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        items.sort(key=lambda x: x["modified_at"], reverse=True)
        return items

    def resolve_media(self, filename: str) -> Path:
        safe = Path(filename).name
        target = (self.media_dir / safe).resolve()
        if target.parent != self.media_dir.resolve() or not target.is_file():
            raise FileNotFoundError(f"Media not found: {safe}")
        return target

    def resolve_audio(self, filename: str) -> Path:
        safe = Path(filename).name
        target = (self.audio_dir / safe).resolve()
        if target.parent != self.audio_dir.resolve() or not target.is_file():
            raise FileNotFoundError(f"Audio not found: {safe}")
        return target

    def resolve_video(self, filename: str) -> Path:
        safe = Path(filename).name
        target = (self.videos_dir / safe).resolve()
        if target.parent != self.videos_dir.resolve() or not target.is_file():
            raise FileNotFoundError(f"Video not found: {safe}")
        return target

    def start_render_video(
        self,
        media_filename: str,
        audio_filename: str,
        output_name: str = "Lyric_Video",
        resolution: str = "1080p",
        lyrics: list[dict[str, Any]] | None = None,
        font_size: int = 54,
        text_color: str = "#FFFFFF",
        outline_color: str = "#000000",
        position: str = "bottom",
        fade_in_ms: int = 350,
        fade_out_ms: int = 350,
        dim_percent: int = 25,
        title_text: str | None = None,
        save_dir: str | None = None,
    ) -> dict[str, Any]:
        if self.has_active_job() or (self.studio_manager and self.studio_manager.has_active_job()):
            raise RuntimeError("Another studio task is already running. Please wait for it to finish.")
        if resolution not in RESOLUTIONS:
            raise ValueError(f"Unsupported resolution: {resolution}")

        media_path = self.resolve_media(media_filename)
        audio_path = self.resolve_audio(audio_filename)

        job_id = uuid.uuid4().hex[:12]
        job = VideoJob(
            job_id=job_id,
            title=f"Video: {output_name}",
            detail=f"Preparing {resolution} MP4 render...",
        )
        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(
            self._run_render_video,
            job_id,
            media_path,
            audio_path,
            output_name,
            resolution,
            lyrics or [],
            font_size,
            text_color,
            outline_color,
            position,
            fade_in_ms,
            fade_out_ms,
            dim_percent,
            title_text,
            save_dir,
        )
        return job.to_dict()

    def _run_render_video(
        self,
        job_id: str,
        media_path: Path,
        audio_path: Path,
        output_name: str,
        resolution: str,
        lyrics: list[dict[str, Any]],
        font_size: int,
        text_color: str,
        outline_color: str,
        position: str,
        fade_in_ms: int,
        fade_out_ms: int,
        dim_percent: int,
        title_text: str | None,
        save_dir: str | None,
    ) -> None:
        ass_path = self.videos_dir / f"_sub_{job_id}.ass"
        try:
            ffmpeg = get_ffmpeg_path()
            if not ffmpeg:
                raise RuntimeError("FFmpeg is required for video rendering.")

            width, height, _ = RESOLUTIONS[resolution]
            duration = probe_audio_duration(audio_path)

            self._update_job(
                job_id,
                status="processing",
                progress=15.0,
                detail="Generating animated ASS lyric overlay...",
            )
            ass_content = build_ass_subtitles(
                lyrics=lyrics,
                width=width,
                height=height,
                font_size=font_size,
                text_color=text_color,
                outline_color=outline_color,
                position=position,
                fade_in_ms=fade_in_ms,
                fade_out_ms=fade_out_ms,
                title_text=title_text,
            )
            ass_path.write_text(ass_content, encoding="utf-8")

            ext = media_path.suffix.lower()
            cmd: list[str] = [ffmpeg, "-y"]

            if ext in IMAGE_EXTS:
                cmd.extend(["-loop", "1", "-framerate", "30", "-i", str(media_path)])
            elif ext in GIF_EXTS:
                cmd.extend(["-ignore_loop", "0", "-i", str(media_path)])
            else:
                # Video background: loop if shorter than audio, strip original audio via -an / -map
                cmd.extend(["-stream_loop", "-1", "-i", str(media_path)])

            cmd.extend(["-i", str(audio_path)])

            # Scale & center-crop to exact target resolution + optional dim + ASS lyric burn
            vf_parts = [
                f"scale={width}:{height}:force_original_aspect_ratio=increase",
                f"crop={width}:{height}",
                "setsar=1",
                "format=yuv420p",
            ]
            dim_alpha = max(0.0, min(0.85, float(dim_percent) / 100.0))
            if dim_alpha > 0.01:
                vf_parts.append(
                    f"drawbox=x=0:y=0:w=iw:h=ih:color=black@{dim_alpha:.2f}:t=fill"
                )
            if lyrics or (title_text and title_text.strip()):
                vf_parts.append(f"ass={_escape_ffmpeg_filter_path(ass_path)}")

            vf_chain = ",".join(vf_parts)
            out_slug = _safe_slug(output_name) or "Lyric_Video"
            out_path = self.videos_dir / f"{out_slug}.mp4"

            self._update_job(
                job_id,
                status="processing",
                progress=45.0,
                detail=f"Rendering {width}x{height} MP4 ({duration:.1f}s)...",
            )

            base_encode = [
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-vf",
                vf_chain,
                "-t",
                f"{duration:.3f}",
                "-c:a",
                "aac",
                "-b:a",
                "256k",
                "-movflags",
                "+faststart",
            ]

            # Try GPU NVENC first, fallback to libx264 cleanly
            nvenc_cmd = cmd + ["-c:v", "h264_nvenc", "-preset", "p4", "-cq", "20"] + base_encode + [str(out_path)]
            proc = subprocess.run(nvenc_cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                x264_cmd = cmd + ["-c:v", "libx264", "-preset", "medium", "-crf", "19"] + base_encode + [str(out_path)]
                proc2 = subprocess.run(x264_cmd, capture_output=True, text=True)
                if proc2.returncode != 0:
                    raise RuntimeError(f"FFmpeg video render failed: {proc2.stderr[-500:]}")

            if save_dir and save_dir.strip():
                import shutil

                dest_dir = Path(save_dir.strip())
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(out_path, dest_dir / out_path.name)

            self._update_job(
                job_id,
                status="completed",
                progress=100.0,
                detail=f"Rendered {out_path.name}",
                output_filename=out_path.name,
            )
        except Exception as exc:
            logger.exception("Video render job %s failed", job_id)
            self._update_job(job_id, status="error", error=str(exc), detail="Failed")
        finally:
            if ass_path.exists():
                try:
                    ass_path.unlink()
                except OSError:
                    pass
