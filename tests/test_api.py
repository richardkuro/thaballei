"""API and service unit tests for Thaballei Audio Studio."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.audio_studio import AudioStudioManager, apply_remaster_dsp
from app.main import app
from app.video_studio import (
    VideoStudioManager,
    build_ass_subtitles,
    parse_lrc_or_text,
)
from app.youtube_service import (
    DownloadManager,
    format_duration,
    get_ffmpeg_path,
    is_youtube_url,
)

client = TestClient(app)


def test_health_and_formats() -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["ffmpeg_available"] is True
    assert get_ffmpeg_path() is not None

    fmt_res = client.get("/api/formats")
    assert fmt_res.status_code == 200
    assert "best" in fmt_res.json()["formats"]
    assert "mp3" in fmt_res.json()["formats"]
    assert "flac" in fmt_res.json()["formats"]


def test_studio_options() -> None:
    res = client.get("/api/studio/options")
    assert res.status_code == 200
    data = res.json()
    assert "htdemucs" in data["stem_models"]
    assert "modern_crisp" in data["remaster_presets"]
    assert "flac" in data["export_formats"]


def test_helpers() -> None:
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("https://music.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube_url("lofi hip hop beats")

    assert format_duration(65) == "1:05"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(None) == "Live / Unknown"


def test_search_endpoint_mocked() -> None:
    fake_results = [
        {
            "id": "abc123",
            "title": "Sample Track",
            "url": "https://www.youtube.com/watch?v=abc123",
            "channel": "Sample Channel",
            "duration": 215,
            "duration_text": "3:35",
            "view_count": 1000,
            "thumbnail": "https://i.ytimg.com/vi/abc123/hqdefault.jpg",
        }
    ]
    with patch("app.main.search_videos", return_value=fake_results):
        res = client.get("/api/search?q=sample+track")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1
    assert body["results"][0]["title"] == "Sample Track"


def test_download_invalid_format() -> None:
    res = client.post(
        "/api/download",
        json={
            "url": "https://www.youtube.com/watch?v=abc123",
            "format": "ogg_invalid",
            "title": "Test",
        },
    )
    assert res.status_code == 400


def test_file_path_traversal_guard(tmp_path: Path) -> None:
    manager = DownloadManager(download_dir=tmp_path)
    sample = tmp_path / "song.mp3"
    sample.write_bytes(b"fake-audio")

    resolved = manager.resolve_file("song.mp3")
    assert resolved == sample.resolve()

    try:
        manager.resolve_file("../secret.txt")
        assert False, "Expected FileNotFoundError"
    except FileNotFoundError:
        pass


def test_remaster_dsp_and_stem_mix(tmp_path: Path) -> None:
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    stereo = np.column_stack((0.25 * np.sin(2 * np.pi * 440 * t), 0.25 * np.sin(2 * np.pi * 440 * t)))

    src_wav = tmp_path / "old_song.wav"
    out_wav = tmp_path / "remastered.wav"
    sf.write(str(src_wav), stereo, sr, subtype="PCM_16")

    apply_remaster_dsp(
        src_wav,
        out_wav,
        preset="modern_crisp",
        noise_reduction=40.0,
        echo_reduction=30.0,
    )
    assert out_wav.exists()
    assert out_wav.stat().st_size > 1000

    lib_dir = tmp_path / "lib"
    stems_dir = tmp_path / "stems"
    set_dir = stems_dir / "track_htdemucs"
    set_dir.mkdir(parents=True, exist_ok=True)
    (set_dir / "_meta.txt").write_text("Old Song.mp3\nhtdemucs\n", encoding="utf-8")
    for name in ("vocals", "drums", "bass", "other"):
        sf.write(str(set_dir / f"{name}.wav"), stereo * 0.2, sr, subtype="PCM_16")

    studio = AudioStudioManager(library_dir=lib_dir, stems_dir=stems_dir)
    result = studio.export_stem_mix(
        stem_set_id="track_htdemucs",
        stems=["drums", "bass", "other"],
        gains={"drums": 1.0, "bass": 1.1, "other": 1.0},
        output_format="mp3",
        remaster_preset="karaoke_master",
        output_label="Karaoke",
    )
    out_file = lib_dir / result["filename"]
    assert out_file.exists()
    assert out_file.suffix == ".mp3"
    assert out_file.stat().st_size > 1000


def test_unified_daw_render(tmp_path: Path) -> None:
    sr = 44100
    t = np.linspace(0, 0.5, sr // 2, endpoint=False, dtype=np.float32)
    stereo = np.column_stack((0.2 * np.sin(2 * np.pi * 220 * t), 0.2 * np.sin(2 * np.pi * 220 * t)))

    lib_dir = tmp_path / "lib"
    stems_dir = tmp_path / "stems"
    lib_dir.mkdir(parents=True, exist_ok=True)
    stems_dir.mkdir(parents=True, exist_ok=True)

    sf.write(str(lib_dir / "backing.wav"), stereo, sr, subtype="PCM_16")
    studio = AudioStudioManager(library_dir=lib_dir, stems_dir=stems_dir)

    job = studio.start_unified_render(
        tracks=[{"source": "library", "filename": "backing.wav", "gain": 0.9, "pan": -0.25}],
        output_name="Test_Master",
        output_format="flac",
        preset="modern_crisp",
        clarity=70,
        bass_boost=60,
        stereo_width=40,
        compression=50,
        noise_reduction=20,
        echo_reduction=15,
        loudness_norm=True,
        master_gain=1.0,
    )
    assert job["kind"] == "render"
    studio._executor.shutdown(wait=True)
    finished = studio.get_job(job["job_id"])
    assert finished is not None
    assert finished["status"] == "completed"
    assert (lib_dir / finished["output_filename"]).exists()


def test_lrc_ass_and_video_render(tmp_path: Path) -> None:
    lrc = "[00:00.20] Hello world\n[00:01.00] Second line"
    parsed = parse_lrc_or_text(lrc, total_duration=5.0)
    assert len(parsed) == 2
    assert parsed[0]["text"] == "Hello world"

    ass = build_ass_subtitles(parsed, width=1280, height=720, fade_in_ms=300, fade_out_ms=300)
    assert "\\fad(300,300)" in ass
    assert "Hello world" in ass

    media_dir = tmp_path / "media"
    audio_dir = tmp_path / "audio"
    videos_dir = tmp_path / "videos"
    media_dir.mkdir()
    audio_dir.mkdir()
    videos_dir.mkdir()

    # Create a tiny valid PNG via matplotlib/PIL? No, pure zlib PNG!
    import struct
    import zlib

    def make_png(path: Path, w: int = 64, h: int = 64) -> None:
        raw = b"".join(b"\x00" + b"\x20\x40\x60" * w for _ in range(h))
        def chunk(tag: bytes, data: bytes) -> bytes:
            return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        ihdr = struct.pack("!IIBBBBB", w, h, 8, 2, 0, 0, 0)
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))

    make_png(media_dir / "bg.png")
    sr = 44100
    t = np.linspace(0, 1.0, sr, endpoint=False, dtype=np.float32)
    stereo = np.column_stack((0.2 * np.sin(2 * np.pi * 330 * t), 0.2 * np.sin(2 * np.pi * 330 * t)))
    sf.write(str(audio_dir / "track.wav"), stereo, sr, subtype="PCM_16")

    vm = VideoStudioManager(media_dir=media_dir, audio_dir=audio_dir, videos_dir=videos_dir)
    job = vm.start_render_video(
        media_filename="bg.png",
        audio_filename="track.wav",
        output_name="Test_Lyric_Vid",
        resolution="720p",
        lyrics=[{"start": 0.1, "end": 0.9, "text": "Hello world"}],
    )
    vm._executor.shutdown(wait=True)
    done = vm.list_jobs()[0]
    assert done["status"] == "completed", done.get("error")
    out_mp4 = videos_dir / done["output_filename"]
    assert out_mp4.exists()
    assert out_mp4.stat().st_size > 1000


def test_youtube_status_and_cookie_endpoints() -> None:
    res = client.get("/api/youtube/status")
    assert res.status_code == 200
    data = res.json()
    assert "cookies_active" in data
    assert "node_available" in data
    assert "detected_browsers" in data

    # Set browser cookies
    res_b = client.post("/api/youtube/cookies/browser", json={"browser": "firefox"})
    assert res_b.status_code == 200
    assert res_b.json()["configured_browser"] == "firefox"

    # Reset
    res_del = client.delete("/api/youtube/cookies")
    assert res_del.status_code == 200
    assert res_del.json()["configured_browser"] is None

    # Test upload cookies
    fake_cookie = b"# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfake-cookie-val\n"
    res_up = client.post(
        "/api/youtube/cookies/upload",
        files={"file": ("cookies.txt", fake_cookie, "text/plain")},
    )
    assert res_up.status_code == 200
    assert res_up.json()["cookies_active"] is True
    assert res_up.json()["source"] == "file"

    # Clean up uploaded test cookie
    res_clean = client.delete("/api/youtube/cookies")
    assert res_clean.status_code == 200
    assert res_clean.json()["cookies_active"] is False
