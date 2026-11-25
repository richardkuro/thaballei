"""Audio Studio service: upload handling, Demucs stem separation, stem mixing, and remastering."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import soundfile as sf
    from pedalboard import (
        Compressor,
        Gain,
        HighShelfFilter,
        HighpassFilter,
        Limiter,
        LowShelfFilter,
        LowpassFilter,
        PeakFilter,
        Pedalboard,
    )

    AUDIO_DSP_AVAILABLE = True
except ImportError:  # pragma: no cover
    np = None  # type: ignore[assignment]
    sf = None  # type: ignore[assignment]
    AUDIO_DSP_AVAILABLE = False

from app.youtube_service import get_ffmpeg_path

logger = logging.getLogger(__name__)

STEM_MODELS: dict[str, dict[str, Any]] = {
    "htdemucs": {
        "label": "4 Stems (Vocals, Drums, Bass, Other)",
        "stems": ["vocals", "drums", "bass", "other"],
        "description": "Fast, high-quality separation for karaoke & remixing",
    },
    "htdemucs_6s": {
        "label": "6 Stems (Vocals, Drums, Bass, Guitar, Piano, Other)",
        "stems": ["vocals", "drums", "bass", "guitar", "piano", "other"],
        "description": "Separates guitar and piano into dedicated stems",
    },
}

REMASTER_PRESETS: dict[str, dict[str, Any]] = {
    "modern_crisp": {
        "label": "Modern Crisp (Best for Old Songs)",
        "description": "Cleans mud, restores airy highs, adds punchy bass & modern loudness",
        "clarity": 65,
        "bass_boost": 55,
        "stereo_width": 35,
        "compression": 0.45,
        "loudness_norm": True,
    },
    "vocal_clarity": {
        "label": "Vocal Clarity & Sparkle",
        "description": "Brings vocals forward with crisp presence and clean low end",
        "clarity": 80,
        "bass_boost": 30,
        "stereo_width": 25,
        "compression": 0.5,
        "loudness_norm": True,
    },
    "warm_punch": {
        "label": "Warm Punchy Bass",
        "description": "Deep modern low-end weight with smooth, non-fatiguing highs",
        "clarity": 40,
        "bass_boost": 80,
        "stereo_width": 30,
        "compression": 0.55,
        "loudness_norm": True,
    },
    "bright_air": {
        "label": "Bright & Airy Restoration",
        "description": "Restores lost high frequencies on muffled or vintage recordings",
        "clarity": 90,
        "bass_boost": 40,
        "stereo_width": 45,
        "compression": 0.4,
        "loudness_norm": True,
    },
    "karaoke_master": {
        "label": "Karaoke Stage Master",
        "description": "Wide, punchy instrumental balance leaving room for live singing",
        "clarity": 55,
        "bass_boost": 60,
        "stereo_width": 55,
        "compression": 0.45,
        "noise_reduction": 10,
        "echo_reduction": 0,
        "loudness_norm": True,
    },
    "clean_studio": {
        "label": "De-Noise & De-Echo Clean",
        "description": "Removes background hiss, room echo, and mud for crisp speech or vocals",
        "clarity": 70,
        "bass_boost": 25,
        "stereo_width": 15,
        "compression": 0.45,
        "noise_reduction": 65,
        "echo_reduction": 50,
        "loudness_norm": True,
    },
}

EXPORT_FORMATS: dict[str, str] = {
    "flac": "FLAC (Lossless)",
    "wav": "WAV (Uncompressed)",
    "mp3": "MP3 (320 kbps)",
    "m4a": "M4A / AAC (256 kbps)",
    "opus": "Opus (192 kbps)",
}


def _safe_slug(name: str) -> str:
    stem = Path(name).stem
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("_")
    return cleaned[:80] or "track"


def _convert_to_wav(input_path: Path, output_wav: Path, sample_rate: int = 44100) -> None:
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for audio conversion.")
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-ac",
        "2",
        "-ar",
        str(sample_rate),
        "-sample_fmt",
        "s16",
        str(output_wav),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg WAV conversion failed: {proc.stderr[-400:]}")


def _encode_audio(
    input_wav: Path,
    output_path: Path,
    target_format: str,
    loudnorm: bool = False,
) -> None:
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required for audio encoding.")

    cmd = [ffmpeg, "-y", "-i", str(input_wav)]
    if loudnorm:
        cmd.extend(["-af", "loudnorm=I=-14:TP=-1.0:LRA=11", "-ar", "48000" if target_format == "opus" else "44100"])

    if target_format == "mp3":
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "320k"])
    elif target_format == "flac":
        cmd.extend(["-c:a", "flac", "-compression_level", "5"])
    elif target_format == "m4a":
        cmd.extend(["-c:a", "aac", "-b:a", "256k"])
    elif target_format == "opus":
        cmd.extend(["-c:a", "libopus", "-b:a", "192k"])
    elif target_format == "wav":
        cmd.extend(["-c:a", "pcm_s16le"])
    else:
        raise ValueError(f"Unsupported export format: {target_format}")

    cmd.append(str(output_path))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"FFmpeg encoding failed: {proc.stderr[-400:]}")


def _apply_stereo_width(audio: np.ndarray, width_pct: float) -> np.ndarray:
    """Adjust stereo width using Mid/Side processing. Expects shape (samples, 2)."""
    if audio.ndim != 2 or audio.shape[1] != 2 or width_pct <= 0:
        return audio
    width = 1.0 + (width_pct / 100.0) * 0.65
    left = audio[:, 0]
    right = audio[:, 1]
    mid = 0.5 * (left + right)
    side = 0.5 * (left - right) * width
    out = np.column_stack((mid + side, mid - side))
    return out.astype(np.float32, copy=False)


def _stft_clean_channel(
    signal: np.ndarray,
    noise_reduction: float,
    echo_reduction: float,
    n_fft: int = 2048,
    hop: int = 512,
) -> np.ndarray:
    """Apply spectral noise gate and late-echo/reverb suppression to a 1D signal."""
    length = len(signal)
    if length < n_fft:
        return signal

    window = np.hanning(n_fft).astype(np.float32)
    pad = n_fft - ((length - n_fft) % hop) if (length - n_fft) % hop != 0 else 0
    padded = np.pad(signal, (0, pad), mode="constant")
    num_frames = 1 + (len(padded) - n_fft) // hop

    # Frame matrix: (num_frames, n_fft)
    strides = (padded.strides[0] * hop, padded.strides[0])
    frames = np.lib.stride_tricks.as_strided(
        padded, shape=(num_frames, n_fft), strides=strides
    )
    spec = np.fft.rfft(frames * window, axis=1)  # (num_frames, freq_bins)
    mag = np.abs(spec)
    phase = np.angle(spec)

    gain = np.ones_like(mag, dtype=np.float32)

    if noise_reduction > 0:
        # Estimate stationary noise floor from quietest 12% of frames per bin
        noise_floor = np.percentile(mag, 12, axis=0, keepdims=True)
        alpha = (noise_reduction / 100.0) * 1.8
        nr_gain = np.maximum(0.08, (mag - alpha * noise_floor) / (mag + 1e-8))
        # Smooth across time frames to reduce musical noise
        if num_frames >= 3:
            nr_gain[1:-1] = 0.25 * nr_gain[:-2] + 0.5 * nr_gain[1:-1] + 0.25 * nr_gain[2:]
        gain *= nr_gain

    if echo_reduction > 0:
        # Late-reflection / echo tail suppression using decaying energy envelope
        beta = (echo_reduction / 100.0) * 0.75
        tail = np.zeros_like(mag[0])
        echo_gain = np.ones_like(mag, dtype=np.float32)
        for idx in range(num_frames):
            cur = mag[idx]
            ratio = np.minimum(1.0, tail / (cur + 1e-8))
            echo_gain[idx] = np.maximum(0.15, 1.0 - beta * ratio)
            tail = 0.84 * tail + 0.16 * cur
        gain *= echo_gain

    cleaned_spec = (mag * gain) * np.exp(1j * phase)
    inv_frames = np.fft.irfft(cleaned_spec, n=n_fft, axis=1) * window

    out = np.zeros(len(padded), dtype=np.float32)
    win_sum = np.zeros(len(padded), dtype=np.float32)
    win_sq = window * window
    for idx in range(num_frames):
        start = idx * hop
        out[start : start + n_fft] += inv_frames[idx]
        win_sum[start : start + n_fft] += win_sq

    nonzero = win_sum > 1e-6
    out[nonzero] /= win_sum[nonzero]
    return out[:length]


def clean_noise_and_echo(
    audio: np.ndarray,
    noise_reduction: float = 0.0,
    echo_reduction: float = 0.0,
) -> np.ndarray:
    """Filter background noise and echo/reverb on stereo audio (samples, channels)."""
    if noise_reduction <= 0 and echo_reduction <= 0:
        return audio
    channels = []
    for ch in range(audio.shape[1]):
        channels.append(
            _stft_clean_channel(audio[:, ch], noise_reduction, echo_reduction)
        )
    return np.column_stack(channels).astype(np.float32, copy=False)


def apply_remaster_dsp(
    input_wav: Path,
    output_wav: Path,
    preset: str = "modern_crisp",
    clarity: float | None = None,
    bass_boost: float | None = None,
    stereo_width: float | None = None,
    noise_reduction: float | None = None,
    echo_reduction: float | None = None,
    compression: float | None = None,
    hp_freq: float | None = None,
    lp_freq: float | None = None,
    bass_freq: float | None = None,
    bass_gain: float | None = None,
    mid_freq: float | None = None,
    mid_gain: float | None = None,
    pres_freq: float | None = None,
    pres_gain: float | None = None,
    air_freq: float | None = None,
    air_gain: float | None = None,
) -> None:
    """Apply noise/echo cleanup, parametric mastering EQ, compression, stereo widening, and limiting."""
    cfg = REMASTER_PRESETS.get(preset, REMASTER_PRESETS["modern_crisp"])
    c_val = float(cfg["clarity"] if clarity is None else clarity)
    b_val = float(cfg["bass_boost"] if bass_boost is None else bass_boost)
    w_val = float(cfg["stereo_width"] if stereo_width is None else stereo_width)
    nr_val = float(cfg.get("noise_reduction", 0) if noise_reduction is None else noise_reduction)
    er_val = float(cfg.get("echo_reduction", 0) if echo_reduction is None else echo_reduction)
    comp_amt = float(cfg["compression"] if compression is None else (float(compression) / 100.0))

    audio, sr = sf.read(str(input_wav), dtype="float32", always_2d=True)
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)

    if nr_val > 0 or er_val > 0:
        audio = clean_noise_and_echo(audio, noise_reduction=nr_val, echo_reduction=er_val)

    # Parametric frequency & gain resolution (falls back to preset-mapped values)
    hp_hz = float(30.0 if hp_freq is None else hp_freq)
    lp_hz = float(20000.0 if lp_freq is None else lp_freq)
    low_hz = float(90.0 if bass_freq is None else bass_freq)
    low_db = float((b_val / 100.0) * 4.5 if bass_gain is None else bass_gain)
    mid_hz = float(300.0 if mid_freq is None else mid_freq)
    mid_db = float(-1.2 - (c_val / 100.0) * 1.3 if mid_gain is None else mid_gain)
    pres_hz = float(3200.0 if pres_freq is None else pres_freq)
    pres_db = float((c_val / 100.0) * 3.5 if pres_gain is None else pres_gain)
    air_hz = float(10000.0 if air_freq is None else air_freq)
    air_db = float((c_val / 100.0) * 4.5 if air_gain is None else air_gain)

    chain = [
        HighpassFilter(cutoff_frequency_hz=max(20.0, min(500.0, hp_hz))),
        LowShelfFilter(cutoff_frequency_hz=max(30.0, min(500.0, low_hz)), gain_db=low_db, q=0.7),
        PeakFilter(cutoff_frequency_hz=max(100.0, min(2000.0, mid_hz)), gain_db=mid_db, q=1.1),
        PeakFilter(cutoff_frequency_hz=max(600.0, min(8000.0, pres_hz)), gain_db=pres_db, q=0.9),
        HighShelfFilter(cutoff_frequency_hz=max(2000.0, min(18000.0, air_hz)), gain_db=air_db, q=0.7),
    ]
    if lp_hz < 19500.0:
        chain.append(LowpassFilter(cutoff_frequency_hz=max(2000.0, min(19500.0, lp_hz))))

    chain.extend(
        [
            Compressor(
                threshold_db=-18.0,
                ratio=1.0 + comp_amt * 2.5,
                attack_ms=12.0,
                release_ms=140.0,
            ),
            Gain(gain_db=1.0),
            Limiter(threshold_db=-1.0, release_ms=100.0),
        ]
    )
    board = Pedalboard(chain)

    # Pedalboard expects (channels, samples)
    processed = board(audio.T, sr).T
    processed = _apply_stereo_width(processed, w_val)

    # Safety peak guard
    peak = float(np.max(np.abs(processed))) if processed.size else 0.0
    if peak > 0.98:
        processed = processed * (0.98 / peak)

    sf.write(str(output_wav), processed, sr, subtype="PCM_16")


@dataclass
class StudioJob:
    """Tracks state for stem separation or remastering jobs."""

    job_id: str
    kind: str  # "separate" | "remaster" | "mix"
    title: str
    status: str = "queued"
    progress: float = 0.0
    detail: str | None = None
    output_filename: str | None = None
    stem_set_id: str | None = None
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AudioStudioManager:
    """Manages stem separation, unified multi-track mixing, and audio remastering."""

    def __init__(self, library_dir: Path, stems_dir: Path, max_workers: int = 1) -> None:
        self.library_dir = library_dir
        self.stems_dir = stems_dir
        self.library_dir.mkdir(parents=True, exist_ok=True)
        self.stems_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._jobs: dict[str, StudioJob] = {}
        self._lock = threading.Lock()

    def has_active_job(self) -> bool:
        with self._lock:
            return any(j.status in ("queued", "processing") for j in self._jobs.values())

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
            for k, v in updates.items():
                setattr(job, k, v)

    def _resolve_library_file(self, filename: str) -> Path:
        safe_name = Path(filename).name
        target = (self.library_dir / safe_name).resolve()
        if target.parent != self.library_dir.resolve() or not target.is_file():
            raise FileNotFoundError(f"Audio file not found: {safe_name}")
        return target

    def start_separation(self, filename: str, model: str = "htdemucs") -> dict[str, Any]:
        if self.has_active_job():
            raise RuntimeError("A studio task is already running. Please wait for it to finish.")
        if model not in STEM_MODELS:
            raise ValueError(f"Unsupported stem model: {model}")
        source_path = self._resolve_library_file(filename)

        job_id = uuid.uuid4().hex[:12]
        stem_set_id = f"{_safe_slug(source_path.name)}_{model}_{job_id[:6]}"
        job = StudioJob(
            job_id=job_id,
            kind="separate",
            title=f"Stems: {source_path.name}",
            stem_set_id=stem_set_id,
            detail=f"Model: {model}",
        )
        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(self._run_separation, job_id, source_path, model, stem_set_id)
        return job.to_dict()

    def _run_separation(
        self, job_id: str, source_path: Path, model: str, stem_set_id: str
    ) -> None:
        work_dir = self.stems_dir / f"_tmp_{job_id}"
        target_dir = self.stems_dir / stem_set_id
        try:
            work_dir.mkdir(parents=True, exist_ok=True)
            target_dir.mkdir(parents=True, exist_ok=True)

            self._update_job(
                job_id,
                status="processing",
                progress=10.0,
                detail="Preparing 44.1 kHz WAV for separation...",
            )
            input_wav = work_dir / "input.wav"
            _convert_to_wav(source_path, input_wav)

            device = "cpu"
            try:
                import torch

                if torch.cuda.is_available():
                    device = "cuda"
            except Exception:
                pass

            self._update_job(
                job_id,
                status="processing",
                progress=25.0,
                detail=f"Separating stems with {model} on {device.upper()}...",
            )

            demucs_out = work_dir / "demucs_out"
            cmd = [
                sys.executable,
                "-m",
                "demucs.separate",
                "-n",
                model,
                "-d",
                device,
                "-o",
                str(demucs_out),
                str(input_wav),
            ]
            env = os.environ.copy()
            ffmpeg = get_ffmpeg_path()
            if ffmpeg:
                env["PATH"] = f"{Path(ffmpeg).parent}{os.pathsep}{env.get('PATH', '')}"

            proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"Demucs separation failed: {(proc.stderr or proc.stdout)[-500:]}"
                )

            # Demucs outputs to <demucs_out>/<model>/<input_stem>/<stem>.wav
            produced_dir = demucs_out / model / "input"
            if not produced_dir.exists():
                raise RuntimeError("Demucs did not produce expected stem files.")

            stem_count = 0
            for wav_file in produced_dir.glob("*.wav"):
                dest = target_dir / wav_file.name
                wav_file.replace(dest)
                stem_count += 1

            # Write metadata marker for listing
            meta_file = target_dir / "_meta.txt"
            meta_file.write_text(f"{source_path.name}\n{model}\n", encoding="utf-8")

            self._update_job(
                job_id,
                status="completed",
                progress=100.0,
                detail=f"Separated {stem_count} stems ({device.upper()})",
                stem_set_id=stem_set_id,
            )
        except Exception as exc:
            logger.exception("Stem separation job %s failed", job_id)
            self._update_job(job_id, status="error", error=str(exc), detail="Failed")
        finally:
            import shutil

            shutil.rmtree(work_dir, ignore_errors=True)

    def list_stem_sets(self) -> list[dict[str, Any]]:
        """List all separated stem sets."""
        sets: list[dict[str, Any]] = []
        if not self.stems_dir.exists():
            return sets

        for folder in self.stems_dir.iterdir():
            if not folder.is_dir() or folder.name.startswith("_tmp_"):
                continue
            wavs = sorted(folder.glob("*.wav"))
            if not wavs:
                continue
            meta_file = folder / "_meta.txt"
            source_name = folder.name
            model = "htdemucs"
            if meta_file.exists():
                lines = meta_file.read_text(encoding="utf-8").splitlines()
                if len(lines) >= 1 and lines[0]:
                    source_name = lines[0]
                if len(lines) >= 2 and lines[1]:
                    model = lines[1]

            stems = [
                {
                    "name": w.stem,
                    "filename": w.name,
                    "size": w.stat().st_size,
                }
                for w in wavs
            ]
            sets.append(
                {
                    "stem_set_id": folder.name,
                    "source_name": source_name,
                    "model": model,
                    "stems": stems,
                    "modified_at": datetime.fromtimestamp(
                        folder.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                }
            )
        sets.sort(key=lambda s: s["modified_at"], reverse=True)
        return sets

    def resolve_stem_file(self, stem_set_id: str, stem_filename: str) -> Path:
        safe_set = Path(stem_set_id).name
        safe_stem = Path(stem_filename).name
        target = (self.stems_dir / safe_set / safe_stem).resolve()
        root = (self.stems_dir / safe_set).resolve()
        if target.parent != root or not target.is_file():
            raise FileNotFoundError("Stem file not found.")
        return target

    def export_stem_mix(
        self,
        stem_set_id: str,
        stems: list[str],
        gains: dict[str, float] | None = None,
        output_format: str = "flac",
        remaster_preset: str | None = None,
        output_label: str | None = None,
        noise_reduction: float = 0.0,
        echo_reduction: float = 0.0,
    ) -> dict[str, Any]:
        """Mix selected stems (with optional remastering) into a single audio file."""
        if output_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported format: {output_format}")
        if not stems:
            raise ValueError("Select at least one stem to export.")

        safe_set = Path(stem_set_id).name
        set_dir = self.stems_dir / safe_set
        if not set_dir.is_dir():
            raise FileNotFoundError("Stem set not found.")

        gains = gains or {}
        mixed: np.ndarray | None = None
        sr_ref: int | None = None

        for stem_name in stems:
            stem_path = set_dir / f"{Path(stem_name).stem}.wav"
            if not stem_path.is_file():
                raise FileNotFoundError(f"Stem '{stem_name}' not found in {safe_set}.")
            data, sr = sf.read(str(stem_path), dtype="float32", always_2d=True)
            gain = max(0.0, min(2.0, float(gains.get(stem_name, 1.0))))
            data = data * gain
            if mixed is None:
                mixed = data
                sr_ref = sr
            else:
                if sr != sr_ref:
                    raise ValueError("Stem sample rates do not match.")
                min_len = min(len(mixed), len(data))
                mixed = mixed[:min_len] + data[:min_len]

        assert mixed is not None and sr_ref is not None

        peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
        if peak > 0.98:
            mixed = mixed * (0.98 / peak)

        tmp_wav = self.stems_dir / f"_mix_{uuid.uuid4().hex[:8]}.wav"
        tmp_master_wav = self.stems_dir / f"_mix_master_{uuid.uuid4().hex[:8]}.wav"
        try:
            sf.write(str(tmp_wav), mixed, sr_ref, subtype="PCM_16")

            loudnorm = False
            encode_src = tmp_wav
            if remaster_preset and remaster_preset != "none":
                apply_remaster_dsp(
                    tmp_wav,
                    tmp_master_wav,
                    preset=remaster_preset,
                    noise_reduction=noise_reduction if noise_reduction > 0 else None,
                    echo_reduction=echo_reduction if echo_reduction > 0 else None,
                )
                encode_src = tmp_master_wav
                loudnorm = bool(
                    REMASTER_PRESETS.get(remaster_preset, {}).get("loudness_norm", True)
                )
            elif noise_reduction > 0 or echo_reduction > 0:
                mixed_cleaned = clean_noise_and_echo(
                    mixed,
                    noise_reduction=noise_reduction,
                    echo_reduction=echo_reduction,
                )
                sf.write(str(tmp_master_wav), mixed_cleaned, sr_ref, subtype="PCM_16")
                encode_src = tmp_master_wav

            meta_file = set_dir / "_meta.txt"
            base_name = safe_set
            if meta_file.exists():
                first_line = meta_file.read_text(encoding="utf-8").splitlines()[0].strip()
                if first_line:
                    base_name = Path(first_line).stem

            tag = output_label or ("+".join(stems))
            if remaster_preset and remaster_preset != "none":
                tag = f"{tag} - {remaster_preset}"
            out_name = f"{base_name} [{tag}].{output_format}"
            out_path = self.library_dir / out_name

            _encode_audio(encode_src, out_path, output_format, loudnorm=loudnorm)
            return {
                "filename": out_path.name,
                "size": out_path.stat().st_size,
                "format": output_format,
            }
        finally:
            for p in (tmp_wav, tmp_master_wav):
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass

    def start_remaster(
        self,
        filename: str,
        preset: str = "modern_crisp",
        output_format: str = "flac",
        clarity: float | None = None,
        bass_boost: float | None = None,
        stereo_width: float | None = None,
        noise_reduction: float | None = None,
        echo_reduction: float | None = None,
        loudness_norm: bool | None = None,
    ) -> dict[str, Any]:
        if self.has_active_job():
            raise RuntimeError("A studio task is already running. Please wait for it to finish.")
        if preset not in REMASTER_PRESETS:
            raise ValueError(f"Unsupported remaster preset: {preset}")
        if output_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}")

        source_path = self._resolve_library_file(filename)
        job_id = uuid.uuid4().hex[:12]
        job = StudioJob(
            job_id=job_id,
            kind="remaster",
            title=f"Remaster: {source_path.name}",
            detail=f"Preset: {REMASTER_PRESETS[preset]['label']}",
        )
        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(
            self._run_remaster,
            job_id,
            source_path,
            preset,
            output_format,
            clarity,
            bass_boost,
            stereo_width,
            noise_reduction,
            echo_reduction,
            loudness_norm,
        )
        return job.to_dict()

    def _run_remaster(
        self,
        job_id: str,
        source_path: Path,
        preset: str,
        output_format: str,
        clarity: float | None,
        bass_boost: float | None,
        stereo_width: float | None,
        noise_reduction: float | None,
        echo_reduction: float | None,
        loudness_norm: bool | None,
    ) -> None:
        tmp_in = self.stems_dir / f"_rem_in_{job_id}.wav"
        tmp_out = self.stems_dir / f"_rem_out_{job_id}.wav"
        try:
            self._update_job(
                job_id, status="processing", progress=20.0, detail="Decoding source audio..."
            )
            _convert_to_wav(source_path, tmp_in)

            self._update_job(
                job_id,
                status="processing",
                progress=55.0,
                detail="Filtering noise/echo & applying studio mastering...",
            )
            apply_remaster_dsp(
                tmp_in,
                tmp_out,
                preset=preset,
                clarity=clarity,
                bass_boost=bass_boost,
                stereo_width=stereo_width,
                noise_reduction=noise_reduction,
                echo_reduction=echo_reduction,
            )

            self._update_job(
                job_id,
                status="processing",
                progress=80.0,
                detail=f"Normalizing & encoding to {output_format.upper()}...",
            )
            use_loudnorm = (
                bool(REMASTER_PRESETS[preset]["loudness_norm"])
                if loudness_norm is None
                else bool(loudness_norm)
            )
            out_name = f"{source_path.stem} [Remastered - {preset}].{output_format}"
            out_path = self.library_dir / out_name
            _encode_audio(tmp_out, out_path, output_format, loudnorm=use_loudnorm)

            self._update_job(
                job_id,
                status="completed",
                progress=100.0,
                detail=f"Saved {out_path.name}",
                output_filename=out_path.name,
            )
        except Exception as exc:
            logger.exception("Remaster job %s failed", job_id)
            self._update_job(job_id, status="error", error=str(exc), detail="Failed")
        finally:
            for p in (tmp_in, tmp_out):
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass

    def start_unified_render(
        self,
        tracks: list[dict[str, Any]],
        output_name: str = "DAW Master",
        output_format: str = "flac",
        preset: str = "modern_crisp",
        clarity: float = 65.0,
        bass_boost: float = 55.0,
        stereo_width: float = 35.0,
        compression: float = 45.0,
        noise_reduction: float = 0.0,
        echo_reduction: float = 0.0,
        loudness_norm: bool = True,
        master_gain: float = 1.0,
        eq_params: dict[str, float] | None = None,
        save_dir: str | None = None,
    ) -> dict[str, Any]:
        """Mix any combination of DAW tracks (library or stems) and apply unified mastering."""
        if self.has_active_job():
            raise RuntimeError("A studio task is already running. Please wait for it to finish.")
        if not tracks:
            raise ValueError("Add at least one track to render.")
        if output_format not in EXPORT_FORMATS:
            raise ValueError(f"Unsupported output format: {output_format}")

        job_id = uuid.uuid4().hex[:12]
        job = StudioJob(
            job_id=job_id,
            kind="render",
            title=f"Render: {output_name}",
            detail=f"Mixing {len(tracks)} track(s) -> {output_format.upper()}",
        )
        with self._lock:
            self._jobs[job_id] = job

        self._executor.submit(
            self._run_unified_render,
            job_id,
            tracks,
            output_name,
            output_format,
            preset,
            clarity,
            bass_boost,
            stereo_width,
            compression,
            noise_reduction,
            echo_reduction,
            loudness_norm,
            master_gain,
            eq_params or {},
            save_dir,
        )
        return job.to_dict()

    def _run_unified_render(
        self,
        job_id: str,
        tracks: list[dict[str, Any]],
        output_name: str,
        output_format: str,
        preset: str,
        clarity: float,
        bass_boost: float,
        stereo_width: float,
        compression: float,
        noise_reduction: float,
        echo_reduction: float,
        loudness_norm: bool,
        master_gain: float,
        eq_params: dict[str, float],
        save_dir: str | None,
    ) -> None:
        tmp_files: list[Path] = []
        tmp_mix = self.stems_dir / f"_render_mix_{job_id}.wav"
        tmp_master = self.stems_dir / f"_render_master_{job_id}.wav"
        tmp_files.extend([tmp_mix, tmp_master])
        try:
            mixed: np.ndarray | None = None
            target_sr = 44100

            for idx, trk in enumerate(tracks):
                self._update_job(
                    job_id,
                    status="processing",
                    progress=round(10 + (idx / max(1, len(tracks))) * 35, 1),
                    detail=f"Decoding track {idx + 1}/{len(tracks)}...",
                )
                kind = trk.get("source", "library")
                if kind == "stem":
                    src_path = self.resolve_stem_file(
                        str(trk["stem_set_id"]), str(trk["filename"])
                    )
                else:
                    src_path = self._resolve_library_file(str(trk["filename"]))

                tmp_wav = self.stems_dir / f"_render_trk_{job_id}_{idx}.wav"
                tmp_files.append(tmp_wav)
                _convert_to_wav(src_path, tmp_wav, sample_rate=target_sr)
                data, _ = sf.read(str(tmp_wav), dtype="float32", always_2d=True)
                if data.shape[1] == 1:
                    data = np.repeat(data, 2, axis=1)

                gain = max(0.0, min(2.0, float(trk.get("gain", 1.0))))
                pan = max(-1.0, min(1.0, float(trk.get("pan", 0.0))))
                # Equal-power stereo panning
                angle = (pan + 1.0) * (np.pi / 4.0)
                left_g = float(np.cos(angle)) * np.sqrt(2.0) * gain
                right_g = float(np.sin(angle)) * np.sqrt(2.0) * gain
                data[:, 0] *= left_g
                data[:, 1] *= right_g

                if mixed is None:
                    mixed = data
                else:
                    if len(data) > len(mixed):
                        pad_len = len(data) - len(mixed)
                        mixed = np.pad(mixed, ((0, pad_len), (0, 0)), mode="constant")
                    elif len(data) < len(mixed):
                        pad_len = len(mixed) - len(data)
                        data = np.pad(data, ((0, pad_len), (0, 0)), mode="constant")
                    mixed = mixed + data

            assert mixed is not None
            mixed = mixed * max(0.0, min(2.0, float(master_gain)))
            peak = float(np.max(np.abs(mixed))) if mixed.size else 0.0
            if peak > 0.98:
                mixed = mixed * (0.98 / peak)

            sf.write(str(tmp_mix), mixed, target_sr, subtype="PCM_16")

            self._update_job(
                job_id,
                status="processing",
                progress=60.0,
                detail="Applying real-time DSP rack (De-Noise, De-Echo, EQ, Width, Comp)...",
            )
            apply_remaster_dsp(
                tmp_mix,
                tmp_master,
                preset=preset,
                clarity=clarity,
                bass_boost=bass_boost,
                stereo_width=stereo_width,
                noise_reduction=noise_reduction,
                echo_reduction=echo_reduction,
                compression=compression,
                hp_freq=eq_params.get("hp_freq"),
                lp_freq=eq_params.get("lp_freq"),
                bass_freq=eq_params.get("bass_freq"),
                bass_gain=eq_params.get("bass_gain"),
                mid_freq=eq_params.get("mid_freq"),
                mid_gain=eq_params.get("mid_gain"),
                pres_freq=eq_params.get("pres_freq"),
                pres_gain=eq_params.get("pres_gain"),
                air_freq=eq_params.get("air_freq"),
                air_gain=eq_params.get("air_gain"),
            )

            self._update_job(
                job_id,
                status="processing",
                progress=85.0,
                detail=f"Normalizing & encoding to {output_format.upper()}...",
            )
            safe_out_stem = _safe_slug(output_name) or "DAW_Master"
            out_path = self.library_dir / f"{safe_out_stem} [DAW Master].{output_format}"
            _encode_audio(tmp_master, out_path, output_format, loudnorm=loudness_norm)

            if save_dir and save_dir.strip():
                import shutil

                dest_dir = Path(save_dir.strip())
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(out_path, dest_dir / out_path.name)

            self._update_job(
                job_id,
                status="completed",
                progress=100.0,
                detail=f"Exported {out_path.name}",
                output_filename=out_path.name,
            )
        except Exception as exc:
            logger.exception("Unified render job %s failed", job_id)
            self._update_job(job_id, status="error", error=str(exc), detail="Failed")
        finally:
            for p in tmp_files:
                if p.exists():
                    try:
                        p.unlink()
                    except OSError:
                        pass
