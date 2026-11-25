# Thaballei Audio Studio

An all-in-one local web application to **find YouTube audio**, **separate instruments & vocals**, **export custom mixes/karaoke**, and **remaster old songs to sound crisp and modern**.

## Features

1. **YouTube Audio Finder & Downloader**
   - Search YouTube by song/artist or paste any `youtube.com`, `youtu.be`, or `music.youtube.com` URL.
   - Download in **Best Native (Opus/M4A, zero re-encoding loss)** or convert to **MP3 (320 kbps)**, **FLAC (Lossless)**, **M4A**, **Opus**, or **WAV** with embedded metadata and cover art.
   - Inspect all raw audio streams before downloading.
2. **Audio Studio: Remastering & Stem Separation**
   - **Upload Local Audio**: Drop in your own old MP3/WAV/FLAC/M4A files or use any track downloaded from YouTube.
   - **Modern Remastering (`Pedalboard` + `FFmpeg loudnorm`)**: Presets like *Modern Crisp (Best for Old Songs)*, *Vocal Clarity & Sparkle*, *Warm Punchy Bass*, *Bright & Airy Restoration*, and *Karaoke Stage Master*, with sliders for Clarity & Air, Bass Punch, Stereo Width, and `-14 LUFS` loudness normalization.
   - **AI Stem Separation (`Demucs`)**: Split any track into **4 stems** (`vocals`, `drums`, `bass`, `other`) or **6 stems** (`+ guitar`, `piano`).
   - **Individual & Custom Mix / Karaoke Export**: Play or save each stem individually, or select any combination (e.g., **Karaoke (No Vocals)**), adjust per-stem levels, optionally apply a remaster preset, and export as a single audio file.

## Run Locally

```powershell
.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 in your browser.
