// === THABALLEI AUDIO DAW // SMOOTH REAL-TIME WEB AUDIO ENGINE & PARAMETRIC DSP ===

const searchForm = document.getElementById("searchForm");
const searchInput = document.getElementById("searchInput");
const formatSelect = document.getElementById("formatSelect");
const formatHint = document.getElementById("formatHint");
const searchBtn = document.getElementById("searchBtn");
const resultsGrid = document.getElementById("resultsGrid");
const resultsCount = document.getElementById("resultsCount");
const filesList = document.getElementById("filesList");
const refreshFilesBtn = document.getElementById("refreshFilesBtn");
const uploadInput = document.getElementById("uploadInput");
const studioUploadInput = document.getElementById("studioUploadInput");
const ffmpegStatus = document.getElementById("ffmpegStatus");
const gpuStatus = document.getElementById("gpuStatus");
const themeToggle = document.getElementById("themeToggle");
const themeLabel = document.getElementById("themeLabel");
const inspectModal = document.getElementById("inspectModal");
const modalTitle = document.getElementById("modalTitle");
const modalBody = document.getElementById("modalBody");
const closeModalBtn = document.getElementById("closeModalBtn");

// Single-Task Pill
const taskDot = document.getElementById("taskDot");
const taskStatusText = document.getElementById("taskStatusText");
const taskDetailText = document.getElementById("taskDetailText");
const taskForwardBtn = document.getElementById("taskForwardBtn");
const taskProgressWrap = document.getElementById("taskProgressWrap");
const taskProgressFill = document.getElementById("taskProgressFill");

// Save Directory Pickers
const dlSaveDirInput = document.getElementById("dlSaveDirInput");
const dlPickDirBtn = document.getElementById("dlPickDirBtn");
const dlClearDirBtn = document.getElementById("dlClearDirBtn");
const dawSaveDirInput = document.getElementById("dawSaveDirInput");
const dawPickDirBtn = document.getElementById("dawPickDirBtn");
const dawClearDirBtn = document.getElementById("dawClearDirBtn");
const vidSaveDirInput = document.getElementById("vidSaveDirInput");
const vidPickDirBtn = document.getElementById("vidPickDirBtn");
const vidClearDirBtn = document.getElementById("vidClearDirBtn");
const forwardDawToVideoBtn = document.getElementById("forwardDawToVideoBtn");

// Navigation
const tabBtns = document.querySelectorAll(".tab-btn");
const tabFinder = document.getElementById("tab-finder");
const tabStudio = document.getElementById("tab-studio");
const tabVideo = document.getElementById("tab-video");

// DAW Transport & Meters
const dawPlayBtn = document.getElementById("dawPlayBtn");
const dawStopBtn = document.getElementById("dawStopBtn");
const dawLoopBtn = document.getElementById("dawLoopBtn");
const dawSpeedSelect = document.getElementById("dawSpeedSelect");
const dawSeek = document.getElementById("dawSeek");
const dawTime = document.getElementById("dawTime");
const dspBypassBtn = document.getElementById("dspBypassBtn");
const spectrumCanvas = document.getElementById("spectrumCanvas");
const vuCanvas = document.getElementById("vuCanvas");

// DAW Tracks & Sources
const libraryAddSelect = document.getElementById("libraryAddSelect");
const addLibraryTrackBtn = document.getElementById("addLibraryTrackBtn");
const separateSelectedBtn = document.getElementById("separateSelectedBtn");
const stemModelSelect = document.getElementById("stemModelSelect");
const stemSetSelect = document.getElementById("stemSetSelect");
const loadStemSetBtn = document.getElementById("loadStemSetBtn");
const dawTracksList = document.getElementById("dawTracksList");
const quickKaraokeBtn = document.getElementById("quickKaraokeBtn");
const quickVocalsBtn = document.getElementById("quickVocalsBtn");
const quickUnmuteBtn = document.getElementById("quickUnmuteBtn");
const clearTracksBtn = document.getElementById("clearTracksBtn");

// Parametric DSP Controls
const remasterPreset = document.getElementById("remasterPreset");
const hpFreqSlider = document.getElementById("hpFreqSlider");
const lpFreqSlider = document.getElementById("lpFreqSlider");
const noiseSlider = document.getElementById("noiseSlider");
const echoSlider = document.getElementById("echoSlider");
const bassFreqSlider = document.getElementById("bassFreqSlider");
const bassGainSlider = document.getElementById("bassGainSlider");
const midFreqSlider = document.getElementById("midFreqSlider");
const midGainSlider = document.getElementById("midGainSlider");
const presFreqSlider = document.getElementById("presFreqSlider");
const presGainSlider = document.getElementById("presGainSlider");
const airFreqSlider = document.getElementById("airFreqSlider");
const airGainSlider = document.getElementById("airGainSlider");
const widthSlider = document.getElementById("widthSlider");
const compSlider = document.getElementById("compSlider");
const masterGainSlider = document.getElementById("masterGainSlider");

const hpFreqVal = document.getElementById("hpFreqVal");
const lpFreqVal = document.getElementById("lpFreqVal");
const noiseVal = document.getElementById("noiseVal");
const echoVal = document.getElementById("echoVal");
const bassFreqVal = document.getElementById("bassFreqVal");
const bassGainVal = document.getElementById("bassGainVal");
const midFreqVal = document.getElementById("midFreqVal");
const midGainVal = document.getElementById("midGainVal");
const presFreqVal = document.getElementById("presFreqVal");
const presGainVal = document.getElementById("presGainVal");
const airFreqVal = document.getElementById("airFreqVal");
const airGainVal = document.getElementById("airGainVal");
const widthVal = document.getElementById("widthVal");
const compVal = document.getElementById("compVal");
const masterGainVal = document.getElementById("masterGainVal");

const exportNameInput = document.getElementById("exportNameInput");
const loudnormCheck = document.getElementById("loudnormCheck");
const remasterFormat = document.getElementById("remasterFormat");
const renderMasterBtn = document.getElementById("renderMasterBtn");

const FORMAT_DESCRIPTIONS = {
  best: "BEST NATIVE: Downloads highest-bitrate original Opus/M4A stream with zero re-encoding loss.",
  mp3: "MP3 (320 KBPS): Universal compatibility with embedded cover art & metadata.",
  flac: "FLAC: Lossless audio container with metadata.",
  m4a: "M4A / AAC: Apple-compatible container with embedded cover art.",
  opus: "OPUS: High-efficiency modern audio codec.",
  wav: "WAV: Uncompressed PCM audio.",
};

let studioOptions = { stem_models: {}, remaster_presets: {}, export_formats: {} };
let taskBusy = false;
let taskPollTimer = null;
let lastDawExportedFile = null;
let pendingForwardToVideo = false;
let pendingTaskForwardAction = null;

function setupFolderPicker(inputEl, pickBtn, clearBtn, storageKey) {
  const saved = localStorage.getItem(storageKey) || "";
  inputEl.value = saved;
  pickBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/api/system/pick-folder", { method: "POST" });
      const data = await res.json();
      if (data.path) {
        inputEl.value = data.path;
        localStorage.setItem(storageKey, data.path);
      }
    } catch {
      alert("Could not open folder picker.");
    }
  });
  clearBtn.addEventListener("click", () => {
    inputEl.value = "";
    localStorage.removeItem(storageKey);
  });
}

setupFolderPicker(dlSaveDirInput, dlPickDirBtn, dlClearDirBtn, "thaballei_dl_dir");
setupFolderPicker(dawSaveDirInput, dawPickDirBtn, dawClearDirBtn, "thaballei_daw_dir");
setupFolderPicker(vidSaveDirInput, vidPickDirBtn, vidClearDirBtn, "thaballei_vid_dir");

async function saveFileWithPicker(url, suggestedName) {
  if (window.showSaveFilePicker) {
    try {
      const handle = await window.showSaveFilePicker({ suggestedName });
      const res = await fetch(url);
      if (!res.ok) throw new Error("Download failed");
      const writable = await handle.createWritable();
      await res.body.pipeTo(writable);
      return;
    } catch (err) {
      if (err.name === "AbortError") return;
    }
  }
  const a = document.createElement("a");
  a.href = `${url}${url.includes("?") ? "&" : "?"}download=1`;
  a.download = suggestedName;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function forwardToDaw(filename) {
  addTrackToDaw({
    name: filename,
    source: "library",
    filename,
    url: `/api/files/${encodeURIComponent(filename)}`,
  });
  exportNameInput.value = filename.replace(/\.[^/.]+$/, "");
  switchTab("studio");
}

function forwardToVideo(filename) {
  if (videoAudioSelect) {
    const exists = Array.from(videoAudioSelect.options).some((o) => o.value === filename);
    if (!exists) {
      const opt = document.createElement("option");
      opt.value = filename;
      opt.textContent = filename;
      videoAudioSelect.appendChild(opt);
    }
    videoAudioSelect.value = filename;
    loadVideoAudioPreview(filename);
    vidOutputName.value = `${filename.replace(/\.[^/.]+$/, "")}_LyricVideo`;
  }
  switchTab("video");
}

taskForwardBtn.addEventListener("click", () => {
  if (pendingTaskForwardAction) {
    pendingTaskForwardAction();
  }
});

// --- Theme (Nothing OS Dark / Light) ---
function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("thaballei_theme", theme);
  themeLabel.textContent = theme === "dark" ? "LIGHT" : "DARK";
}
applyTheme(localStorage.getItem("thaballei_theme") || "dark");
themeToggle.addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme") || "dark";
  applyTheme(cur === "dark" ? "light" : "dark");
});

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function formatBytes(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let val = bytes;
  let idx = 0;
  while (val >= 1024 && idx < units.length - 1) {
    val /= 1024;
    idx += 1;
  }
  return `${val.toFixed(1)} ${units[idx]}`;
}

function formatTime(secs) {
  if (!Number.isFinite(secs) || secs < 0) return "00:00.0";
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  const d = Math.floor((secs % 1) * 10);
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}.${d}`;
}

function formatDb(val) {
  const num = Number(val);
  return num > 0 ? `+${num.toFixed(1)}` : num.toFixed(1);
}

function switchTab(tabName) {
  tabBtns.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabName));
  tabFinder.classList.toggle("hidden", tabName !== "finder");
  tabStudio.classList.toggle("hidden", tabName !== "studio");
  tabVideo.classList.toggle("hidden", tabName !== "video");
}
tabBtns.forEach((btn) => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

formatSelect.addEventListener("change", () => {
  formatHint.textContent = FORMAT_DESCRIPTIONS[formatSelect.value] || "";
});

// =========================================================================
// SMOOTH REAL-TIME WEB AUDIO DAW GRAPH (ZERO CHOPPING / SOFT-CLIP SAFETY)
// =========================================================================
let audioCtx = null;
let dawBus = null;
let dawTracks = [];
let isPlaying = false;
let isLooping = false;
let isBypassed = false;
let isSeeking = false;
let animFrameId = null;

function createSoftClipCurve() {
  // Smooth analog tanh saturation curve: prevents abrupt digital cutoffs & limiter pumping
  const n = 4096;
  const curve = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const x = (i * 2) / n - 1;
    curve[i] = Math.tanh(x * 1.15) / Math.tanh(1.15);
  }
  return curve;
}

function ensureAudioGraph() {
  if (audioCtx) return;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  audioCtx = new Ctx();

  const inputSum = audioCtx.createGain();
  // -3 dB internal summing headroom so multi-stem sums + EQ boosts never slam into clipping
  inputSum.gain.value = 0.72;

  const dryGain = audioCtx.createGain();
  const wetGain = audioCtx.createGain();

  const highpass = audioCtx.createBiquadFilter();
  highpass.type = "highpass";
  highpass.Q.value = 0.7;

  const lowpass = audioCtx.createBiquadFilter();
  lowpass.type = "lowpass";
  lowpass.Q.value = 0.7;

  const lowShelf = audioCtx.createBiquadFilter();
  lowShelf.type = "lowshelf";

  const midPeak = audioCtx.createBiquadFilter();
  midPeak.type = "peaking";
  midPeak.Q.value = 1.0;

  const presPeak = audioCtx.createBiquadFilter();
  presPeak.type = "peaking";
  presPeak.Q.value = 0.9;

  const airShelf = audioCtx.createBiquadFilter();
  airShelf.type = "highshelf";

  // Mid/Side Stereo Width Matrix
  const msSplit = audioCtx.createChannelSplitter(2);
  const msMerge = audioCtx.createChannelMerger(2);
  const midL = audioCtx.createGain();
  const midR = audioCtx.createGain();
  const sideL = audioCtx.createGain();
  const sideR = audioCtx.createGain();

  // Gentle Glue Compressor (smooth knee, never chops)
  const compressor = audioCtx.createDynamicsCompressor();
  compressor.threshold.value = -16;
  compressor.knee.value = 24;
  compressor.ratio.value = 2.0;
  compressor.attack.value = 0.018;
  compressor.release.value = 0.2;

  // Transparent Analog Soft-Clipper (replaces harsh brickwall limiter)
  const softClipper = audioCtx.createWaveShaper();
  softClipper.curve = createSoftClipCurve();
  softClipper.oversample = "2x";

  const masterGain = audioCtx.createGain();
  masterGain.gain.value = 1.0;

  const analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  analyser.smoothingTimeConstant = 0.8;

  const vuSplit = audioCtx.createChannelSplitter(2);
  const analyserL = audioCtx.createAnalyser();
  const analyserR = audioCtx.createAnalyser();
  analyserL.fftSize = 256;
  analyserR.fftSize = 256;

  // Dry path
  inputSum.connect(dryGain);
  dryGain.connect(masterGain);

  // Wet DSP path
  inputSum.connect(highpass);
  highpass.connect(lowpass);
  lowpass.connect(lowShelf);
  lowShelf.connect(midPeak);
  midPeak.connect(presPeak);
  presPeak.connect(airShelf);

  airShelf.connect(msSplit);
  msSplit.connect(midL, 0);
  msSplit.connect(sideL, 1);
  msSplit.connect(midR, 1);
  msSplit.connect(sideR, 0);
  midL.connect(msMerge, 0, 0);
  sideL.connect(msMerge, 0, 0);
  midR.connect(msMerge, 0, 1);
  sideR.connect(msMerge, 0, 1);

  msMerge.connect(compressor);
  compressor.connect(softClipper);
  softClipper.connect(wetGain);
  wetGain.connect(masterGain);

  masterGain.connect(analyser);
  masterGain.connect(vuSplit);
  vuSplit.connect(analyserL, 0);
  vuSplit.connect(analyserR, 1);
  masterGain.connect(audioCtx.destination);

  dawBus = {
    inputSum,
    dryGain,
    wetGain,
    highpass,
    lowpass,
    lowShelf,
    midPeak,
    presPeak,
    airShelf,
    midL,
    midR,
    sideL,
    sideR,
    compressor,
    masterGain,
    analyser,
    analyserL,
    analyserR,
  };

  applyRealtimeDsp();
  startMetersLoop();
}

function applyRealtimeDsp() {
  if (!dawBus || !audioCtx) return;
  const now = audioCtx.currentTime;
  const tau = 0.06; // 60ms smooth ramp: zero clicks, zero cutoffs

  const hpHz = Number(hpFreqSlider.value);
  const lpHz = Number(lpFreqSlider.value);
  const nr = Number(noiseSlider.value);
  const er = Number(echoSlider.value);
  const bassHz = Number(bassFreqSlider.value);
  const bassDb = Number(bassGainSlider.value);
  const midHz = Number(midFreqSlider.value);
  const midDb = Number(midGainSlider.value);
  const presHz = Number(presFreqSlider.value);
  const presDb = Number(presGainSlider.value);
  const airHz = Number(airFreqSlider.value);
  const airDb = Number(airGainSlider.value);
  const width = Number(widthSlider.value);
  const comp = Number(compSlider.value);
  const master = Number(masterGainSlider.value) / 100.0;

  dawBus.dryGain.gain.setTargetAtTime(isBypassed ? 1.0 : 0.0, now, 0.03);
  dawBus.wetGain.gain.setTargetAtTime(isBypassed ? 0.0 : 1.0, now, 0.03);

  // Gentle HP/LP + Noise Filter offset (never aggressively chops off)
  const effectiveHp = Math.min(350, hpHz + (nr / 100.0) * 45);
  const effectiveLp = Math.max(5000, lpHz - (nr / 100.0) * 1800);
  dawBus.highpass.frequency.setTargetAtTime(effectiveHp, now, tau);
  dawBus.lowpass.frequency.setTargetAtTime(effectiveLp, now, tau);

  // Full Parametric EQ (20Hz - 20kHz)
  dawBus.lowShelf.frequency.setTargetAtTime(bassHz, now, tau);
  dawBus.lowShelf.gain.setTargetAtTime(bassDb, now, tau);

  dawBus.midPeak.frequency.setTargetAtTime(midHz, now, tau);
  dawBus.midPeak.gain.setTargetAtTime(midDb - (er / 100.0) * 1.5, now, tau);

  dawBus.presPeak.frequency.setTargetAtTime(presHz, now, tau);
  dawBus.presPeak.gain.setTargetAtTime(presDb + (er / 100.0) * 0.8, now, tau);

  dawBus.airShelf.frequency.setTargetAtTime(airHz, now, tau);
  dawBus.airShelf.gain.setTargetAtTime(airDb, now, tau);

  // Stereo Width
  const wFactor = Math.max(0.3, 1.0 + (width / 100.0) * 0.55 - (er / 100.0) * 0.35);
  const mainCoeff = 0.5 * (1.0 + wFactor);
  const crossCoeff = 0.5 * (1.0 - wFactor);
  dawBus.midL.gain.setTargetAtTime(mainCoeff, now, tau);
  dawBus.midR.gain.setTargetAtTime(mainCoeff, now, tau);
  dawBus.sideL.gain.setTargetAtTime(crossCoeff, now, tau);
  dawBus.sideR.gain.setTargetAtTime(crossCoeff, now, tau);

  // Smooth Compressor
  dawBus.compressor.ratio.setTargetAtTime(1.0 + (comp / 100.0) * 3.0, now, tau);
  dawBus.compressor.threshold.setTargetAtTime(-10 - (comp / 100.0) * 12, now, tau);

  dawBus.masterGain.gain.setTargetAtTime(master, now, 0.03);
}

function startMetersLoop() {
  if (animFrameId) return;
  const sCtx = spectrumCanvas.getContext("2d");
  const vCtx = vuCanvas.getContext("2d");
  const freqData = new Uint8Array(dawBus.analyser.frequencyBinCount);
  const timeL = new Uint8Array(dawBus.analyserL.fftSize);
  const timeR = new Uint8Array(dawBus.analyserR.fftSize);

  function draw() {
    animFrameId = requestAnimationFrame(draw);
    const isLight = document.documentElement.getAttribute("data-theme") === "light";
    const bg = isLight ? "#ececf1" : "#050506";
    const barColor = isLight ? "#0c0c0f" : "#f5f5f7";
    const accent = "#d71921";

    const sw = (spectrumCanvas.width = spectrumCanvas.clientWidth || 400);
    const sh = (spectrumCanvas.height = 44);
    sCtx.fillStyle = bg;
    sCtx.fillRect(0, 0, sw, sh);

    dawBus.analyser.getByteFrequencyData(freqData);
    const barCount = 48;
    const step = Math.max(1, Math.floor(freqData.length / barCount));
    const barW = sw / barCount;
    for (let i = 0; i < barCount; i++) {
      const val = freqData[i * step] / 255.0;
      const h = val * (sh - 4);
      sCtx.fillStyle = val > 0.8 ? accent : barColor;
      sCtx.fillRect(i * barW + 1, sh - h, Math.max(2, barW - 2), h);
    }

    const vw = (vuCanvas.width = vuCanvas.clientWidth || 180);
    const vh = (vuCanvas.height = 44);
    vCtx.fillStyle = bg;
    vCtx.fillRect(0, 0, vw, vh);

    const calcPeak = (arr) => {
      let peak = 0;
      for (let i = 0; i < arr.length; i++) {
        const v = Math.abs((arr[i] - 128) / 128);
        if (v > peak) peak = v;
      }
      return Math.min(1, peak);
    };
    dawBus.analyserL.getByteTimeDomainData(timeL);
    dawBus.analyserR.getByteTimeDomainData(timeR);
    const pL = calcPeak(timeL);
    const pR = calcPeak(timeR);

    const drawBar = (y, label, level) => {
      vCtx.fillStyle = isLight ? "#61616b" : "#8b8b96";
      vCtx.font = "9px JetBrains Mono, monospace";
      vCtx.fillText(label, 6, y + 10);
      const x0 = 20;
      const maxW = vw - 26;
      vCtx.fillStyle = isLight ? "#d5d5de" : "#1e1e25";
      vCtx.fillRect(x0, y + 2, maxW, 10);
      vCtx.fillStyle = level > 0.88 ? accent : "#22c55e";
      vCtx.fillRect(x0, y + 2, maxW * level, 10);
    };
    drawBar(5, "L", pL);
    drawBar(24, "R", pR);
  }
  draw();
}

// =========================================================================
// DAW TRACK MANAGEMENT
// =========================================================================

const blobUrlCache = new Map();

async function getFastAudioUrl(url) {
  if (blobUrlCache.has(url)) return blobUrlCache.get(url);
  try {
    const res = await fetch(url);
    if (!res.ok) return url;
    const blob = await res.blob();
    const objUrl = URL.createObjectURL(blob);
    blobUrlCache.set(url, objUrl);
    return objUrl;
  } catch {
    return url;
  }
}

async function addTrackToDaw({ name, source, filename, stem_set_id = null, url }) {
  ensureAudioGraph();
  const id = `trk_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

  const fastUrl = await getFastAudioUrl(url);
  const audio = new Audio(fastUrl);
  audio.preload = "auto";
  audio.loop = isLooping;
  audio.playbackRate = Number(dawSpeedSelect.value);

  const mediaSrc = audioCtx.createMediaElementSource(audio);
  const gainNode = audioCtx.createGain();
  const panNode = audioCtx.createStereoPanner();

  mediaSrc.connect(gainNode);
  gainNode.connect(panNode);
  panNode.connect(dawBus.inputSum);

  const track = {
    id,
    name,
    source,
    filename,
    stem_set_id,
    url,
    audio,
    mediaSrc,
    gainNode,
    panNode,
    gain: 1.0,
    pan: 0.0,
    muted: false,
    solo: false,
    included: true,
  };

  if (dawTracks.length === 0) {
    attachMasterTimeEvents(track);
  } else if (dawTracks[0]?.audio) {
    audio.currentTime = dawTracks[0].audio.currentTime || 0;
  }

  dawTracks.push(track);
  lastDawExportedFile = null;
  updateTrackAudioNodes();
  renderDawTracks();
  if (isPlaying) {
    audio.play().catch(() => {});
  }
}

function attachMasterTimeEvents(track) {
  track.audio.addEventListener("loadedmetadata", () => {
    dawSeek.max = String(track.audio.duration || 100);
    dawTime.textContent = `${formatTime(track.audio.currentTime)} / ${formatTime(track.audio.duration)}`;
  });
  track.audio.addEventListener("timeupdate", () => {
    if (!isSeeking) {
      dawSeek.value = String(track.audio.currentTime || 0);
    }
    dawTime.textContent = `${formatTime(track.audio.currentTime)} / ${formatTime(track.audio.duration)}`;
  });
  track.audio.addEventListener("ended", () => {
    if (!isLooping) {
      isPlaying = false;
      dawPlayBtn.textContent = "▶ PLAY";
    }
  });
}

function removeTrackFromDaw(trackId) {
  const idx = dawTracks.findIndex((t) => t.id === trackId);
  if (idx === -1) return;
  const [removed] = dawTracks.splice(idx, 1);
  removed.audio.pause();
  removed.mediaSrc.disconnect();
  removed.gainNode.disconnect();
  removed.panNode.disconnect();

  if (idx === 0 && dawTracks.length > 0) {
    attachMasterTimeEvents(dawTracks[0]);
  } else if (dawTracks.length === 0) {
    isPlaying = false;
    dawPlayBtn.textContent = "▶ PLAY";
    dawSeek.value = "0";
    dawTime.textContent = "00:00.0 / 00:00.0";
  }
  updateTrackAudioNodes();
  renderDawTracks();
}

function clearDawTracks() {
  while (dawTracks.length) {
    removeTrackFromDaw(dawTracks[0].id);
  }
}

function updateTrackAudioNodes() {
  if (!audioCtx) return;
  const now = audioCtx.currentTime;
  const anySolo = dawTracks.some((t) => t.solo);
  for (const t of dawTracks) {
    const audible = anySolo ? t.solo && !t.muted : !t.muted;
    t.gainNode.gain.setTargetAtTime(audible ? t.gain : 0.0, now, 0.04);
    t.panNode.pan.setTargetAtTime(t.pan, now, 0.04);
  }
}

function renderDawTracks() {
  if (!dawTracks.length) {
    dawTracksList.innerHTML = `<div class="empty-state mono">NO TRACKS LOADED. ADD A TRACK, UPLOAD A FILE, OR SEPARATE STEMS ABOVE.</div>`;
    return;
  }

  dawTracksList.innerHTML = "";
  const anySolo = dawTracks.some((t) => t.solo);

  for (const t of dawTracks) {
    const audible = anySolo ? t.solo && !t.muted : !t.muted;
    const strip = document.createElement("div");
    strip.className = `daw-track-strip${audible ? "" : " muted-track"}`;

    const panLabel =
      Math.abs(t.pan) < 0.03 ? "C" : t.pan < 0 ? `${Math.round(Math.abs(t.pan) * 100)}L` : `${Math.round(t.pan * 100)}R`;

    strip.innerHTML = `
      <div class="track-top">
        <div class="track-title-wrap">
          <input type="checkbox" class="trk-include" ${t.included ? "checked" : ""} title="Include in export" />
          <span class="badge mono">${t.source === "stem" ? "STEM" : "AUD"}</span>
          <span class="track-title" title="${escapeHtml(t.name)}">${escapeHtml(t.name)}</span>
        </div>
        <div class="row-gap">
          <button type="button" class="daw-ms-btn trk-mute ${t.muted ? "active-mute" : ""}" title="Mute">M</button>
          <button type="button" class="daw-ms-btn trk-solo ${t.solo ? "active-solo" : ""}" title="Solo">S</button>
          <button type="button" class="danger-btn trk-remove" title="Remove">✕</button>
        </div>
      </div>
      <div class="track-controls">
        <div class="slider-row">
          <label>VOL <span class="trk-gain-val">${Math.round(t.gain * 100)}</span>%</label>
          <input type="range" class="trk-gain" min="0" max="150" value="${Math.round(t.gain * 100)}" />
        </div>
        <div class="slider-row">
          <label>PAN <span class="trk-pan-val">${panLabel}</span></label>
          <input type="range" class="trk-pan" min="-100" max="100" value="${Math.round(t.pan * 100)}" />
        </div>
      </div>
    `;

    strip.querySelector(".trk-include").addEventListener("change", (e) => {
      t.included = e.target.checked;
    });
    strip.querySelector(".trk-mute").addEventListener("click", () => {
      t.muted = !t.muted;
      updateTrackAudioNodes();
      renderDawTracks();
    });
    strip.querySelector(".trk-solo").addEventListener("click", () => {
      t.solo = !t.solo;
      updateTrackAudioNodes();
      renderDawTracks();
    });
    strip.querySelector(".trk-remove").addEventListener("click", () => {
      removeTrackFromDaw(t.id);
    });

    const gainSlider = strip.querySelector(".trk-gain");
    const gainText = strip.querySelector(".trk-gain-val");
    gainSlider.addEventListener("input", () => {
      t.gain = Number(gainSlider.value) / 100.0;
      gainText.textContent = gainSlider.value;
      updateTrackAudioNodes();
    });

    const panSlider = strip.querySelector(".trk-pan");
    const panText = strip.querySelector(".trk-pan-val");
    panSlider.addEventListener("input", () => {
      t.pan = Number(panSlider.value) / 100.0;
      const p = Number(panSlider.value);
      panText.textContent = Math.abs(p) < 3 ? "C" : p < 0 ? `${Math.abs(p)}L` : `${p}R`;
      updateTrackAudioNodes();
    });

    dawTracksList.appendChild(strip);
  }
}

dawPlayBtn.addEventListener("click", async () => {
  if (!dawTracks.length) return;
  ensureAudioGraph();
  if (audioCtx.state === "suspended") await audioCtx.resume();

  if (isPlaying) {
    dawTracks.forEach((t) => t.audio.pause());
    isPlaying = false;
    dawPlayBtn.textContent = "▶ PLAY";
  } else {
    const syncTime = dawTracks[0].audio.currentTime || 0;
    dawTracks.forEach((t) => {
      if (Math.abs(t.audio.currentTime - syncTime) > 0.15) {
        t.audio.currentTime = syncTime;
      }
    });
    await Promise.all(dawTracks.map((t) => t.audio.play().catch(() => {})));
    isPlaying = true;
    dawPlayBtn.textContent = "⏸ PAUSE";
  }
});

dawStopBtn.addEventListener("click", () => {
  dawTracks.forEach((t) => {
    t.audio.pause();
    t.audio.currentTime = 0;
  });
  isPlaying = false;
  dawPlayBtn.textContent = "▶ PLAY";
  dawSeek.value = "0";
  if (dawTracks[0]?.audio) {
    dawTime.textContent = `00:00.0 / ${formatTime(dawTracks[0].audio.duration)}`;
  }
});

dawLoopBtn.addEventListener("click", () => {
  isLooping = !isLooping;
  dawTracks.forEach((t) => (t.audio.loop = isLooping));
  dawLoopBtn.textContent = `LOOP: ${isLooping ? "ON" : "OFF"}`;
  dawLoopBtn.classList.toggle("active-toggle", isLooping);
});

dawSpeedSelect.addEventListener("change", () => {
  const rate = Number(dawSpeedSelect.value);
  dawTracks.forEach((t) => (t.audio.playbackRate = rate));
});

dawSeek.addEventListener("input", () => {
  isSeeking = true;
  if (dawTracks[0]?.audio) {
    dawTime.textContent = `${formatTime(Number(dawSeek.value))} / ${formatTime(dawTracks[0].audio.duration)}`;
  }
});
dawSeek.addEventListener("change", () => {
  const val = Number(dawSeek.value);
  dawTracks.forEach((t) => (t.audio.currentTime = val));
  isSeeking = false;
});

dspBypassBtn.addEventListener("click", () => {
  isBypassed = !isBypassed;
  dspBypassBtn.textContent = isBypassed ? "DSP: BYPASS" : "DSP: ON";
  dspBypassBtn.classList.toggle("bypassed", isBypassed);
  applyRealtimeDsp();
});

quickKaraokeBtn.addEventListener("click", () => {
  dawTracks.forEach((t) => {
    const isVocal = t.name.toLowerCase().includes("vocal");
    t.muted = isVocal;
    t.included = !isVocal;
    t.solo = false;
  });
  updateTrackAudioNodes();
  renderDawTracks();
});

quickVocalsBtn.addEventListener("click", () => {
  dawTracks.forEach((t) => {
    const isVocal = t.name.toLowerCase().includes("vocal");
    t.muted = !isVocal;
    t.included = isVocal;
    t.solo = false;
  });
  updateTrackAudioNodes();
  renderDawTracks();
});

quickUnmuteBtn.addEventListener("click", () => {
  dawTracks.forEach((t) => {
    t.muted = false;
    t.included = true;
    t.solo = false;
  });
  updateTrackAudioNodes();
  renderDawTracks();
});

clearTracksBtn.addEventListener("click", clearDawTracks);

// =========================================================================
// SINGLE ACTIVE TASK POLLER
// =========================================================================

function setTaskUi(busy, statusText, detailText = "", pct = 0) {
  taskBusy = busy;
  taskDot.classList.toggle("busy", busy);
  taskStatusText.textContent = statusText;
  taskDetailText.textContent = detailText;
  if (busy) {
    taskProgressWrap.classList.remove("hidden");
    taskProgressFill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  } else {
    taskProgressWrap.classList.add("hidden");
  }
  separateSelectedBtn.disabled = busy;
  renderMasterBtn.disabled = busy;
  if (renderVideoBtn) renderVideoBtn.disabled = busy;
}

async function pollTasks() {
  try {
    const [dlRes, stRes, vidRes] = await Promise.all([
      fetch("/api/jobs"),
      fetch("/api/studio/jobs"),
      fetch("/api/video/jobs"),
    ]);
    const dlData = await dlRes.json();
    const stData = await stRes.json();
    const vidData = await vidRes.json();

    const activeDl = (dlData.jobs || []).find((j) =>
      ["queued", "downloading", "processing"].includes(j.status)
    );
    const activeSt = (stData.jobs || []).find((j) =>
      ["queued", "processing"].includes(j.status)
    );
    const activeVid = (vidData.jobs || []).find((j) =>
      ["queued", "processing"].includes(j.status)
    );

    const active = activeVid || activeSt || activeDl;
    if (active) {
      const detail = active.speed ? `${active.progress}% • ${active.speed}` : `${active.progress}%`;
      taskForwardBtn.classList.add("hidden");
      pendingTaskForwardAction = null;
      setTaskUi(true, active.title || "BUSY", detail, active.progress || 0);
      if (!taskPollTimer) taskPollTimer = setInterval(pollTasks, 1000);
      return;
    }

    if (taskPollTimer) {
      clearInterval(taskPollTimer);
      taskPollTimer = null;
      await refreshFiles();
      await refreshStemSets();
      await refreshRenderedVideos();

      const latestDl = (dlData.jobs || [])[0];
      const latestSt = (stData.jobs || [])[0];
      const latestVid = (vidData.jobs || [])[0];

      if (latestSt && latestSt.kind === "separate" && latestSt.status === "completed" && latestSt.stem_set_id) {
        await loadStemSetIntoDaw(latestSt.stem_set_id, true);
      }
      if (latestSt && latestSt.kind === "render" && latestSt.status === "completed" && latestSt.output_filename) {
        lastDawExportedFile = latestSt.output_filename;
        if (pendingForwardToVideo) {
          pendingForwardToVideo = false;
          forwardToVideo(latestSt.output_filename);
        } else {
          pendingTaskForwardAction = () => forwardToVideo(latestSt.output_filename);
          taskForwardBtn.textContent = "→ VIDEO";
          taskForwardBtn.classList.remove("hidden");
        }
      } else if (latestDl && latestDl.status === "completed" && latestDl.filename) {
        pendingTaskForwardAction = () => forwardToDaw(latestDl.filename);
        taskForwardBtn.textContent = "→ DAW";
        taskForwardBtn.classList.remove("hidden");
      }

      const latestAny = latestVid || latestSt || latestDl;
      if (latestAny && latestAny.status === "error") {
        pendingForwardToVideo = false;
        setTaskUi(false, "ERROR", latestAny.error || "Failed", 0);
        return;
      }
    }
    setTaskUi(false, "IDLE", "", 0);
  } catch {
    // ignore
  }
}

// =========================================================================
// API ACTIONS & PARAMETRIC DSP SYNC
// =========================================================================

async function checkHealth() {
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.ffmpeg_available) {
      ffmpegStatus.textContent = "FFMPEG: READY";
      ffmpegStatus.classList.add("ok");
    } else {
      ffmpegStatus.textContent = "FFMPEG: MISSING";
    }
    if (data.cuda_available) {
      gpuStatus.textContent = `CUDA: ${data.gpu_name || "READY"}`;
      gpuStatus.classList.add("ok");
    } else {
      gpuStatus.textContent = "COMPUTE: CPU";
    }
  } catch {
    ffmpegStatus.textContent = "OFFLINE";
    gpuStatus.textContent = "OFFLINE";
  }
}

async function loadStudioOptions() {
  try {
    const res = await fetch("/api/studio/options");
    studioOptions = await res.json();

    remasterPreset.innerHTML = "";
    for (const [key, cfg] of Object.entries(studioOptions.remaster_presets || {})) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = cfg.label;
      remasterPreset.appendChild(opt);
    }
    syncPresetSliders();

    remasterFormat.innerHTML = "";
    for (const [key, label] of Object.entries(studioOptions.export_formats || {})) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = label;
      remasterFormat.appendChild(opt);
    }

    stemModelSelect.innerHTML = "";
    for (const [key, cfg] of Object.entries(studioOptions.stem_models || {})) {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = cfg.label;
      stemModelSelect.appendChild(opt);
    }
  } catch {
    // ignore
  }
}

function syncPresetSliders() {
  const cfg = (studioOptions.remaster_presets || {})[remasterPreset.value];
  if (!cfg) return;
  hpFreqSlider.value = 30;
  lpFreqSlider.value = 20000;
  noiseSlider.value = cfg.noise_reduction ?? 0;
  echoSlider.value = cfg.echo_reduction ?? 0;
  bassFreqSlider.value = 90;
  bassGainSlider.value = ((cfg.bass_boost ?? 55) / 100.0) * 4.5;
  midFreqSlider.value = 300;
  midGainSlider.value = -1.2 - ((cfg.clarity ?? 65) / 100.0) * 1.3;
  presFreqSlider.value = 3200;
  presGainSlider.value = ((cfg.clarity ?? 65) / 100.0) * 3.5;
  airFreqSlider.value = 10000;
  airGainSlider.value = ((cfg.clarity ?? 65) / 100.0) * 4.5;
  widthSlider.value = cfg.stereo_width ?? 35;
  compSlider.value = Math.round((cfg.compression ?? 0.45) * 100);
  loudnormCheck.checked = Boolean(cfg.loudness_norm);
  updateDspReadouts();
  applyRealtimeDsp();
}

function updateDspReadouts() {
  hpFreqVal.textContent = hpFreqSlider.value;
  lpFreqVal.textContent = lpFreqSlider.value;
  noiseVal.textContent = noiseSlider.value;
  echoVal.textContent = echoSlider.value;
  bassFreqVal.textContent = bassFreqSlider.value;
  bassGainVal.textContent = formatDb(bassGainSlider.value);
  midFreqVal.textContent = midFreqSlider.value;
  midGainVal.textContent = formatDb(midGainSlider.value);
  presFreqVal.textContent = presFreqSlider.value;
  presGainVal.textContent = formatDb(presGainSlider.value);
  airFreqVal.textContent = airFreqSlider.value;
  airGainVal.textContent = formatDb(airGainSlider.value);
  widthVal.textContent = widthSlider.value;
  compVal.textContent = compSlider.value;
  masterGainVal.textContent = masterGainSlider.value;
}

remasterPreset.addEventListener("change", syncPresetSliders);
[
  hpFreqSlider,
  lpFreqSlider,
  noiseSlider,
  echoSlider,
  bassFreqSlider,
  bassGainSlider,
  midFreqSlider,
  midGainSlider,
  presFreqSlider,
  presGainSlider,
  airFreqSlider,
  airGainSlider,
  widthSlider,
  compSlider,
  masterGainSlider,
].forEach((el) => {
  el.addEventListener("input", () => {
    updateDspReadouts();
    applyRealtimeDsp();
  });
});

searchForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const query = searchInput.value.trim();
  if (!query) return;
  searchBtn.disabled = true;
  searchBtn.textContent = "SEARCHING...";
  resultsGrid.innerHTML = `<div class="empty-state mono">SEARCHING YOUTUBE FOR "${escapeHtml(query)}"...</div>`;
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=12`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Search failed");
    renderResults(data.results || []);
  } catch (err) {
    resultsGrid.innerHTML = `<div class="empty-state mono">ERROR: ${escapeHtml(err.message)}</div>`;
  } finally {
    searchBtn.disabled = false;
    searchBtn.textContent = "FIND VIDEO";
  }
});

function renderResults(results) {
  resultsCount.textContent = `${results.length} ITEM${results.length === 1 ? "" : "S"}`;
  if (!results.length) {
    resultsGrid.innerHTML = `<div class="empty-state mono">NO VIDEOS FOUND.</div>`;
    return;
  }
  resultsGrid.innerHTML = "";
  for (const item of results) {
    const card = document.createElement("article");
    card.className = "video-card";
    card.innerHTML = `
      <div class="thumb-wrap">
        <img src="${escapeHtml(item.thumbnail || "")}" alt="${escapeHtml(item.title)}" loading="lazy" />
        <span class="duration-badge">${escapeHtml(item.duration_text || "")}</span>
      </div>
      <div class="card-body">
        <div class="video-title" title="${escapeHtml(item.title)}">${escapeHtml(item.title)}</div>
        <div class="video-meta">${escapeHtml(item.channel)}</div>
        <div class="card-actions">
          <button type="button" class="download-btn">DOWNLOAD</button>
          <button type="button" class="ghost-btn inspect-btn">STREAMS</button>
        </div>
      </div>
    `;
    card.querySelector(".download-btn").addEventListener("click", () => queueDownload(item));
    card.querySelector(".inspect-btn").addEventListener("click", () => inspectStreams(item));
    resultsGrid.appendChild(card);
  }
}

async function queueDownload(item) {
  if (taskBusy) {
    alert("A task is already running. Please wait for it to finish (1 task at a time).");
    return;
  }
  const res = await fetch("/api/download", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      url: item.url,
      format: formatSelect.value,
      title: item.title,
      save_dir: dlSaveDirInput.value || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(`Download error: ${data.detail || "Failed"}`);
    return;
  }
  await pollTasks();
}

async function inspectStreams(item) {
  modalTitle.textContent = item.title;
  modalBody.innerHTML = "INSPECTING AUDIO STREAMS...";
  inspectModal.classList.remove("hidden");
  try {
    const res = await fetch(`/api/inspect?url=${encodeURIComponent(item.url)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Inspection failed");
    const streams = data.streams || [];
    if (!streams.length) {
      modalBody.innerHTML = "<p>NO SEPARATE AUDIO-ONLY STREAMS REPORTED.</p>";
      return;
    }
    const rows = streams
      .map(
        (s, idx) => `
        <tr>
          <td>${idx === 0 ? "<strong>BEST</strong> " : ""}${escapeHtml(s.format_id)}</td>
          <td>${escapeHtml(s.ext)}</td>
          <td>${escapeHtml(s.acodec)}</td>
          <td>${s.abr ? `${s.abr} kbps` : "—"}</td>
          <td>${s.asr ? `${s.asr} Hz` : "—"}</td>
          <td>${formatBytes(s.filesize)}</td>
        </tr>`
      )
      .join("");
    modalBody.innerHTML = `
      <table class="stream-table">
        <thead><tr><th>ID</th><th>EXT</th><th>CODEC</th><th>BITRATE</th><th>SAMPLE</th><th>SIZE</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    `;
  } catch (err) {
    modalBody.innerHTML = `<p>ERROR: ${escapeHtml(err.message)}</p>`;
  }
}

closeModalBtn.addEventListener("click", () => inspectModal.classList.add("hidden"));
inspectModal.addEventListener("click", (e) => {
  if (e.target === inspectModal) inspectModal.classList.add("hidden");
});

async function handleFileUpload(file, autoAddToDaw = false) {
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/studio/upload", { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) {
    alert(`Upload failed: ${data.detail || "Unknown error"}`);
    return;
  }
  await refreshFiles();
  libraryAddSelect.value = data.filename;
  if (autoAddToDaw) {
    addTrackToDaw({
      name: data.filename,
      source: "library",
      filename: data.filename,
      url: `/api/files/${encodeURIComponent(data.filename)}`,
    });
  }
}

uploadInput.addEventListener("change", async (e) => {
  await handleFileUpload(e.target.files[0], false);
  e.target.value = "";
});

studioUploadInput.addEventListener("change", async (e) => {
  await handleFileUpload(e.target.files[0], true);
  e.target.value = "";
});

async function refreshFiles() {
  try {
    const res = await fetch("/api/files");
    const data = await res.json();
    const files = data.files || [];
    renderFiles(files);
    populateLibrarySelect(files);
  } catch {
    // ignore
  }
}

function populateLibrarySelect(files) {
  const prev = libraryAddSelect.value;
  const prevVid = videoAudioSelect ? videoAudioSelect.value : "";
  libraryAddSelect.innerHTML = `<option value="">-- SELECT AUDIO FILE --</option>`;
  if (videoAudioSelect) {
    videoAudioSelect.innerHTML = `<option value="">-- SELECT AUDIO TRACK --</option>`;
  }
  for (const f of files) {
    const opt = document.createElement("option");
    opt.value = f.name;
    opt.textContent = `${f.name} (${formatBytes(f.size)})`;
    libraryAddSelect.appendChild(opt);
    if (videoAudioSelect) {
      videoAudioSelect.appendChild(opt.cloneNode(true));
    }
  }
  if (prev && files.some((f) => f.name === prev)) {
    libraryAddSelect.value = prev;
  } else if (files.length && !libraryAddSelect.value) {
    libraryAddSelect.value = files[0].name;
  }
  if (videoAudioSelect) {
    if (prevVid && files.some((f) => f.name === prevVid)) {
      videoAudioSelect.value = prevVid;
    } else if (files.length && !videoAudioSelect.value) {
      videoAudioSelect.value = files[0].name;
      loadVideoAudioPreview(files[0].name);
    }
  }
}

function renderFiles(files) {
  if (!files.length) {
    filesList.innerHTML = `<div class="empty-state small mono">EMPTY // DOWNLOAD OR UPLOAD AUDIO</div>`;
    return;
  }
  filesList.innerHTML = "";
  for (const file of files) {
    const row = document.createElement("div");
    row.className = "file-item";
    const encoded = encodeURIComponent(file.name);
    row.innerHTML = `
      <div class="file-name">${escapeHtml(file.name)}</div>
      <div class="muted mono small-text">${escapeHtml(file.ext.toUpperCase())} • ${formatBytes(file.size)}</div>
      <div class="file-actions">
        <button type="button" class="ghost-btn daw-open-btn">→ DAW</button>
        <button type="button" class="ghost-btn vid-open-btn">→ VIDEO</button>
        <button type="button" class="ghost-btn save-as-btn">SAVE AS</button>
        <button type="button" class="danger-btn del-btn">DEL</button>
      </div>
    `;
    row.querySelector(".daw-open-btn").addEventListener("click", () => forwardToDaw(file.name));
    row.querySelector(".vid-open-btn").addEventListener("click", () => forwardToVideo(file.name));
    row.querySelector(".save-as-btn").addEventListener("click", () => {
      saveFileWithPicker(`/api/files/${encoded}`, file.name);
    });
    row.querySelector(".del-btn").addEventListener("click", async () => {
      await fetch(`/api/files/${encoded}`, { method: "DELETE" });
      await refreshFiles();
    });
    filesList.appendChild(row);
  }
}

addLibraryTrackBtn.addEventListener("click", () => {
  const filename = libraryAddSelect.value;
  if (!filename) {
    alert("Select an audio file from the library first.");
    return;
  }
  addTrackToDaw({
    name: filename,
    source: "library",
    filename,
    url: `/api/files/${encodeURIComponent(filename)}`,
  });
  if (!exportNameInput.value || exportNameInput.value === "DAW_Master") {
    exportNameInput.value = filename.replace(/\.[^/.]+$/, "");
  }
});

separateSelectedBtn.addEventListener("click", async () => {
  if (taskBusy) {
    alert("A task is already running. Please wait for it to finish (1 task at a time).");
    return;
  }
  const filename = libraryAddSelect.value;
  if (!filename) {
    alert("Select an audio file to separate first.");
    return;
  }
  const res = await fetch("/api/studio/separate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ filename, model: stemModelSelect.value }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(`Separation failed: ${data.detail || "Unknown error"}`);
    return;
  }
  await pollTasks();
});

forwardDawToVideoBtn.addEventListener("click", () => {
  if (lastDawExportedFile) {
    forwardToVideo(lastDawExportedFile);
    return;
  }
  if (dawTracks.some((t) => t.included)) {
    pendingForwardToVideo = true;
    renderMasterBtn.click();
    return;
  }
  if (libraryAddSelect.value) {
    forwardToVideo(libraryAddSelect.value);
    return;
  }
  alert("Load or export a track first to forward to Video Studio.");
});

async function refreshStemSets() {
  try {
    const res = await fetch("/api/studio/stems");
    const data = await res.json();
    const sets = data.stem_sets || [];
    stemSetSelect.innerHTML = `<option value="">-- STEMS --</option>`;
    for (const s of sets) {
      const opt = document.createElement("option");
      opt.value = s.stem_set_id;
      opt.textContent = `${s.source_name} (${s.model})`;
      stemSetSelect.appendChild(opt);
    }
    stemSetSelect._sets = sets;
  } catch {
    // ignore
  }
}

async function loadStemSetIntoDaw(stemSetId, replaceExisting = false) {
  await refreshStemSets();
  const sets = stemSetSelect._sets || [];
  const set = sets.find((s) => s.stem_set_id === stemSetId);
  if (!set) return;
  if (replaceExisting) clearDawTracks();
  for (const stem of set.stems) {
    addTrackToDaw({
      name: `${stem.name.toUpperCase()} (${set.source_name})`,
      source: "stem",
      filename: stem.filename,
      stem_set_id: set.stem_set_id,
      url: `/api/studio/stems/${encodeURIComponent(set.stem_set_id)}/${encodeURIComponent(stem.filename)}`,
    });
  }
  exportNameInput.value = set.source_name.replace(/\.[^/.]+$/, "");
}

loadStemSetBtn.addEventListener("click", () => {
  const id = stemSetSelect.value;
  if (!id) {
    alert("Select a saved stem set first.");
    return;
  }
  loadStemSetIntoDaw(id, false);
});

renderMasterBtn.addEventListener("click", async () => {
  if (taskBusy) {
    alert("A task is already running. Please wait for it to finish (1 task at a time).");
    return;
  }
  const activeTracks = dawTracks.filter((t) => t.included);
  if (!activeTracks.length) {
    alert("Add and check at least one track in the DAW console to render.");
    return;
  }

  const res = await fetch("/api/studio/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      tracks: activeTracks.map((t) => ({
        source: t.source,
        filename: t.filename,
        stem_set_id: t.stem_set_id,
        gain: t.gain,
        pan: t.pan,
      })),
      output_name: exportNameInput.value.trim() || "DAW_Master",
      output_format: remasterFormat.value,
      preset: remasterPreset.value,
      stereo_width: Number(widthSlider.value),
      compression: Number(compSlider.value),
      noise_reduction: Number(noiseSlider.value),
      echo_reduction: Number(echoSlider.value),
      loudness_norm: loudnormCheck.checked,
      master_gain: Number(masterGainSlider.value) / 100.0,
      save_dir: dawSaveDirInput.value || null,
      eq_params: {
        hp_freq: Number(hpFreqSlider.value),
        lp_freq: Number(lpFreqSlider.value),
        bass_freq: Number(bassFreqSlider.value),
        bass_gain: Number(bassGainSlider.value),
        mid_freq: Number(midFreqSlider.value),
        mid_gain: Number(midGainSlider.value),
        pres_freq: Number(presFreqSlider.value),
        pres_gain: Number(presGainSlider.value),
        air_freq: Number(airFreqSlider.value),
        air_gain: Number(airGainSlider.value),
      },
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(`Render failed: ${data.detail || "Unknown error"}`);
    return;
  }
  await pollTasks();
});

forwardDawToVideoBtn.addEventListener("click", () => {
  if (lastDawExportedFile) {
    forwardToVideo(lastDawExportedFile);
    return;
  }
  if (dawTracks.some((t) => t.included)) {
    pendingForwardToVideo = true;
    renderMasterBtn.click();
    return;
  }
  if (libraryAddSelect.value) {
    forwardToVideo(libraryAddSelect.value);
    return;
  }
  alert("Load or export a track first to forward to Video Studio.");
});

refreshFilesBtn.addEventListener("click", refreshFiles);

// =========================================================================
// 03 // VIDEO & LYRIC / KARAOKE STUDIO
// =========================================================================

const videoMediaSelect = document.getElementById("videoMediaSelect");
const videoMediaUpload = document.getElementById("videoMediaUpload");
const videoAudioSelect = document.getElementById("videoAudioSelect");
const videoPreviewCanvas = document.getElementById("videoPreviewCanvas");
const hiddenBgVideo = document.getElementById("hiddenBgVideo");
const vidPlayBtn = document.getElementById("vidPlayBtn");
const vidStopBtn = document.getElementById("vidStopBtn");
const vidSeek = document.getElementById("vidSeek");
const vidTime = document.getElementById("vidTime");
const renderedVideosList = document.getElementById("renderedVideosList");
const refreshVideosBtn = document.getElementById("refreshVideosBtn");

const vidTapBtn = document.getElementById("vidTapBtn");
const vidAddLineBtn = document.getElementById("vidAddLineBtn");
const lyricRawInput = document.getElementById("lyricRawInput");
const parseLyricsBtn = document.getElementById("parseLyricsBtn");
const lyricRowsList = document.getElementById("lyricRowsList");

const vidResSelect = document.getElementById("vidResSelect");
const vidPosSelect = document.getElementById("vidPosSelect");
const vidFontSlider = document.getElementById("vidFontSlider");
const vidFontVal = document.getElementById("vidFontVal");
const vidDimSlider = document.getElementById("vidDimSlider");
const vidDimVal = document.getElementById("vidDimVal");
const vidFadeInSlider = document.getElementById("vidFadeInSlider");
const vidFadeInVal = document.getElementById("vidFadeInVal");
const vidFadeOutSlider = document.getElementById("vidFadeOutSlider");
const vidFadeOutVal = document.getElementById("vidFadeOutVal");
const vidColorInput = document.getElementById("vidColorInput");
const vidTitleInput = document.getElementById("vidTitleInput");
const vidOutputName = document.getElementById("vidOutputName");
const renderVideoBtn = document.getElementById("renderVideoBtn");

let vidAudio = new Audio();
let vidIsPlaying = false;
let vidIsSeeking = false;
let vidBgImage = null;
let vidBgKind = "none"; // "image" | "video" | "none"
let vidLyrics = []; // [{ start, end, text }]
let vidTapIndex = 0;
let videoResolutions = {};

async function loadVideoOptions() {
  try {
    const res = await fetch("/api/video/options");
    const data = await res.json();
    videoResolutions = data.resolutions || {};
    vidResSelect.innerHTML = "";
    for (const [k, info] of Object.entries(videoResolutions)) {
      const opt = document.createElement("option");
      opt.value = k;
      opt.textContent = info.label;
      vidResSelect.appendChild(opt);
    }
  } catch {
    // ignore
  }
}

async function refreshVideoMedia() {
  try {
    const res = await fetch("/api/video/media");
    const data = await res.json();
    const media = data.media || [];
    const prev = videoMediaSelect.value;
    videoMediaSelect.innerHTML = `<option value="">-- SELECT PHOTO / GIF / VIDEO --</option>`;
    for (const m of media) {
      const opt = document.createElement("option");
      opt.value = m.name;
      opt.dataset.kind = m.kind;
      opt.textContent = `[${m.kind.toUpperCase()}] ${m.name}`;
      videoMediaSelect.appendChild(opt);
    }
    if (prev && media.some((m) => m.name === prev)) {
      videoMediaSelect.value = prev;
    } else if (media.length && !videoMediaSelect.value) {
      videoMediaSelect.value = media[0].name;
      loadBackgroundMedia(media[0].name, media[0].kind);
    }
  } catch {
    // ignore
  }
}

function loadBackgroundMedia(filename, kindHint = null) {
  if (!filename) {
    vidBgKind = "none";
    vidBgImage = null;
    hiddenBgVideo.pause();
    hiddenBgVideo.src = "";
    return;
  }
  const url = `/api/video/media/${encodeURIComponent(filename)}`;
  const ext = filename.split(".").pop().toLowerCase();
  const isVideo = kindHint === "video" || ["mp4", "mov", "webm", "mkv", "avi"].includes(ext);

  if (isVideo) {
    vidBgKind = "video";
    vidBgImage = null;
    hiddenBgVideo.src = url;
    hiddenBgVideo.load();
    if (vidIsPlaying) hiddenBgVideo.play().catch(() => {});
  } else {
    vidBgKind = "image";
    hiddenBgVideo.pause();
    hiddenBgVideo.src = "";
    const img = new Image();
    img.onload = () => {
      vidBgImage = img;
    };
    img.src = url;
  }
}

videoMediaSelect.addEventListener("change", () => {
  const opt = videoMediaSelect.selectedOptions[0];
  loadBackgroundMedia(videoMediaSelect.value, opt?.dataset?.kind);
});

videoMediaUpload.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/video/upload-media", { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) {
    alert(`Media upload failed: ${data.detail || "Error"}`);
    return;
  }
  await refreshVideoMedia();
  videoMediaSelect.value = data.filename;
  loadBackgroundMedia(data.filename);
  e.target.value = "";
});

async function loadVideoAudioPreview(filename) {
  vidAudio.pause();
  vidIsPlaying = false;
  vidPlayBtn.textContent = "▶ PREVIEW";
  if (!filename) {
    vidAudio.src = "";
    return;
  }
  const fastUrl = await getFastAudioUrl(`/api/files/${encodeURIComponent(filename)}`);
  vidAudio.src = fastUrl;
  vidAudio.preload = "auto";
  vidAudio.load();
}

videoAudioSelect.addEventListener("change", () => {
  loadVideoAudioPreview(videoAudioSelect.value);
  if (videoAudioSelect.value) {
    vidOutputName.value = `${videoAudioSelect.value.replace(/\.[^/.]+$/, "")}_LyricVideo`;
  }
});

vidAudio.addEventListener("loadedmetadata", () => {
  vidSeek.max = String(vidAudio.duration || 100);
  vidTime.textContent = `${formatTime(0)} / ${formatTime(vidAudio.duration)}`;
});

vidAudio.addEventListener("timeupdate", () => {
  if (!vidIsSeeking) vidSeek.value = String(vidAudio.currentTime || 0);
  vidTime.textContent = `${formatTime(vidAudio.currentTime)} / ${formatTime(vidAudio.duration)}`;
});

vidAudio.addEventListener("ended", () => {
  vidIsPlaying = false;
  vidPlayBtn.textContent = "▶ PREVIEW";
  hiddenBgVideo.pause();
});

vidPlayBtn.addEventListener("click", async () => {
  if (!videoAudioSelect.value) {
    alert("Select an audio track first.");
    return;
  }
  if (vidIsPlaying) {
    vidAudio.pause();
    hiddenBgVideo.pause();
    vidIsPlaying = false;
    vidPlayBtn.textContent = "▶ PREVIEW";
  } else {
    await vidAudio.play().catch(() => {});
    if (vidBgKind === "video") hiddenBgVideo.play().catch(() => {});
    vidIsPlaying = true;
    vidPlayBtn.textContent = "⏸ PAUSE";
  }
});

vidStopBtn.addEventListener("click", () => {
  vidAudio.pause();
  vidAudio.currentTime = 0;
  hiddenBgVideo.pause();
  hiddenBgVideo.currentTime = 0;
  vidIsPlaying = false;
  vidPlayBtn.textContent = "▶ PREVIEW";
  vidSeek.value = "0";
  vidTapIndex = 0;
});

vidSeek.addEventListener("input", () => {
  vidIsSeeking = true;
  vidTime.textContent = `${formatTime(Number(vidSeek.value))} / ${formatTime(vidAudio.duration)}`;
});
vidSeek.addEventListener("change", () => {
  vidAudio.currentTime = Number(vidSeek.value);
  vidIsSeeking = false;
});

// Enforce strictly sequential, non-overlapping lyrics
function enforceNonOverlappingLyrics(changedIndex = -1) {
  if (!vidLyrics.length) return;
  vidLyrics.sort((a, b) => a.start - b.start);
  const minDur = 0.3;
  for (let i = 0; i < vidLyrics.length; i++) {
    const item = vidLyrics[i];
    item.start = Math.max(0, Number(item.start) || 0);
    item.end = Math.max(item.start + minDur, Number(item.end) || item.start + minDur);
    if (i > 0) {
      const prev = vidLyrics[i - 1];
      if (item.start < prev.end) {
        if (changedIndex === i) {
          // User dragged/edited current item's start earlier -> trim previous end if possible
          if (item.start >= prev.start + minDur) {
            prev.end = Number((item.start - 0.02).toFixed(2));
          } else {
            item.start = Number((prev.end + 0.02).toFixed(2));
          }
        } else {
          item.start = Number((prev.end + 0.02).toFixed(2));
        }
        item.end = Math.max(item.start + minDur, item.end);
      }
    }
    item.start = Number(item.start.toFixed(2));
    item.end = Number(item.end.toFixed(2));
  }
}

// Lyric Editor & Tap-to-Sync
function renderLyricRows() {
  enforceNonOverlappingLyrics();
  if (!vidLyrics.length) {
    lyricRowsList.innerHTML = `<div class="empty-state small mono">NO LYRICS YET. PASTE TEXT ABOVE OR CLICK + LINE.</div>`;
    return;
  }
  lyricRowsList.innerHTML = "";
  vidLyrics.forEach((item, idx) => {
    const row = document.createElement("div");
    row.className = "lyric-row";
    row.innerHTML = `
      <input type="number" step="0.1" min="0" class="lyr-start" value="${item.start}" title="Start (s)" />
      <input type="number" step="0.1" min="0" class="lyr-end" value="${item.end}" title="End (s)" />
      <input type="text" class="lyr-text" value="${escapeHtml(item.text)}" placeholder="Lyric line..." />
      <button type="button" class="danger-btn lyr-del" title="Delete line">✕</button>
    `;
    const startInp = row.querySelector(".lyr-start");
    const endInp = row.querySelector(".lyr-end");
    startInp.addEventListener("change", (e) => {
      item.start = Math.max(0, Number(e.target.value) || 0);
      enforceNonOverlappingLyrics(idx);
      renderLyricRows();
    });
    endInp.addEventListener("change", (e) => {
      item.end = Math.max(item.start + 0.3, Number(e.target.value) || item.start + 0.3);
      enforceNonOverlappingLyrics(idx);
      renderLyricRows();
    });
    row.querySelector(".lyr-text").addEventListener("input", (e) => {
      item.text = e.target.value;
    });
    row.querySelector(".lyr-del").addEventListener("click", () => {
      vidLyrics.splice(idx, 1);
      renderLyricRows();
    });
    lyricRowsList.appendChild(row);
  });
}

parseLyricsBtn.addEventListener("click", async () => {
  const raw = lyricRawInput.value.trim();
  if (!raw) return;
  const res = await fetch("/api/video/parse-lyrics", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      raw_text: raw,
      audio_filename: videoAudioSelect.value || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert("Failed to parse lyrics.");
    return;
  }
  vidLyrics = data.lyrics || [];
  vidTapIndex = 0;
  renderLyricRows();
});

vidAddLineBtn.addEventListener("click", () => {
  const lastEnd = vidLyrics.length ? vidLyrics[vidLyrics.length - 1].end + 0.1 : 0;
  const t = Math.max(lastEnd, Number((vidAudio.currentTime || 0).toFixed(2)));
  vidLyrics.push({ start: t, end: Number((t + 3.0).toFixed(2)), text: "New lyric line" });
  renderLyricRows();
});

vidTapBtn.addEventListener("click", () => {
  const now = Number((vidAudio.currentTime || 0).toFixed(2));
  if (!vidLyrics.length) {
    vidLyrics.push({ start: now, end: now + 3.0, text: "Line 1" });
    vidTapIndex = 1;
    renderLyricRows();
    return;
  }
  if (vidTapIndex > 0 && vidTapIndex - 1 < vidLyrics.length) {
    vidLyrics[vidTapIndex - 1].end = Math.max(
      vidLyrics[vidTapIndex - 1].start + 0.3,
      Number((now - 0.05).toFixed(2))
    );
  }
  if (vidTapIndex < vidLyrics.length) {
    const minStart = vidTapIndex > 0 ? vidLyrics[vidTapIndex - 1].end + 0.05 : 0;
    vidLyrics[vidTapIndex].start = Math.max(minStart, now);
    vidLyrics[vidTapIndex].end = Number((vidLyrics[vidTapIndex].start + 3.5).toFixed(2));
    vidTapIndex += 1;
  } else {
    vidTapIndex = 0;
  }
  renderLyricRows();
});

// =========================================================================
// DRAGGABLE NON-OVERLAPPING LYRIC TIMELINE CANVAS
// =========================================================================
const lyricTimelineCanvas = document.getElementById("lyricTimelineCanvas");
let tlDragState = null; // { idx, mode: 'move'|'left'|'right', startX, origStart, origEnd }

function getTimelineDuration() {
  const audDur = Number.isFinite(vidAudio.duration) && vidAudio.duration > 0 ? vidAudio.duration : 0;
  const maxLyr = vidLyrics.reduce((m, l) => Math.max(m, l.end), 0);
  return Math.max(audDur, maxLyr + 2, 15);
}

function drawLyricTimeline() {
  requestAnimationFrame(drawLyricTimeline);
  if (!lyricTimelineCanvas || tabVideo.classList.contains("hidden")) return;

  const ctx = lyricTimelineCanvas.getContext("2d");
  const w = (lyricTimelineCanvas.width = lyricTimelineCanvas.clientWidth || 500);
  const h = (lyricTimelineCanvas.height = 44);
  const isLight = document.documentElement.getAttribute("data-theme") === "light";

  ctx.fillStyle = isLight ? "#ececf1" : "#08080a";
  ctx.fillRect(0, 0, w, h);

  const dur = getTimelineDuration();
  const now = vidAudio.currentTime || 0;

  vidLyrics.forEach((item, idx) => {
    const x1 = (item.start / dur) * w;
    const x2 = (item.end / dur) * w;
    const bw = Math.max(8, x2 - x1);
    const active = now >= item.start && now <= item.end;

    ctx.fillStyle = active ? "#d71921" : isLight ? "#c6c6d2" : "#262632";
    ctx.fillRect(x1, 6, bw, h - 12);
    ctx.strokeStyle = isLight ? "#888" : "#444455";
    ctx.strokeRect(x1, 6, bw, h - 12);

    // Resize handle bars
    ctx.fillStyle = isLight ? "#333" : "#aaa";
    ctx.fillRect(x1, 6, 3, h - 12);
    ctx.fillRect(x1 + bw - 3, 6, 3, h - 12);

    if (bw > 28) {
      ctx.fillStyle = active ? "#fff" : isLight ? "#111" : "#e5e5ea";
      ctx.font = "10px JetBrains Mono, monospace";
      ctx.fillText(item.text.slice(0, Math.floor(bw / 6.5)), x1 + 6, 26);
    }
  });

  // Playhead
  const px = (now / dur) * w;
  ctx.fillStyle = "#d71921";
  ctx.fillRect(px - 1, 0, 2, h);
}
drawLyricTimeline();

if (lyricTimelineCanvas) {
  lyricTimelineCanvas.addEventListener("mousedown", (e) => {
    const rect = lyricTimelineCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const w = rect.width || 1;
    const dur = getTimelineDuration();
    const clickTime = (x / w) * dur;

    for (let i = 0; i < vidLyrics.length; i++) {
      const item = vidLyrics[i];
      const x1 = (item.start / dur) * w;
      const x2 = (item.end / dur) * w;
      if (x >= x1 - 4 && x <= x2 + 4) {
        let mode = "move";
        if (Math.abs(x - x1) <= 6) mode = "left";
        else if (Math.abs(x - x2) <= 6) mode = "right";
        tlDragState = {
          idx: i,
          mode,
          startX: x,
          origStart: item.start,
          origEnd: item.end,
        };
        return;
      }
    }
    // Clicked empty space -> seek audio
    if (vidAudio.src) {
      vidAudio.currentTime = Math.max(0, Math.min(dur, clickTime));
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (!tlDragState) return;
    const rect = lyricTimelineCanvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const w = rect.width || 1;
    const dur = getTimelineDuration();
    const dt = ((x - tlDragState.startX) / w) * dur;
    const idx = tlDragState.idx;
    const item = vidLyrics[idx];
    const minBound = idx > 0 ? vidLyrics[idx - 1].end + 0.02 : 0;
    const maxBound = idx + 1 < vidLyrics.length ? vidLyrics[idx + 1].start - 0.02 : dur;
    const minDur = 0.3;

    if (tlDragState.mode === "move") {
      const span = tlDragState.origEnd - tlDragState.origStart;
      let newStart = Math.max(minBound, Math.min(maxBound - span, tlDragState.origStart + dt));
      item.start = Number(newStart.toFixed(2));
      item.end = Number((newStart + span).toFixed(2));
    } else if (tlDragState.mode === "left") {
      item.start = Number(
        Math.max(minBound, Math.min(item.end - minDur, tlDragState.origStart + dt)).toFixed(2)
      );
    } else if (tlDragState.mode === "right") {
      item.end = Number(
        Math.min(maxBound, Math.max(item.start + minDur, tlDragState.origEnd + dt)).toFixed(2)
      );
    }
  });

  window.addEventListener("mouseup", () => {
    if (tlDragState) {
      tlDragState = null;
      renderLyricRows();
    }
  });
}

// =========================================================================
// YOUTUBE & DAW KEYBOARD SHORTCUTS (SPACE/K, J/L, ARROWS, M, 0-9, ,/., ESC)
// =========================================================================
document.addEventListener("keydown", (e) => {
  const tag = (e.target && e.target.tagName) || "";
  if (["INPUT", "TEXTAREA", "SELECT"].includes(tag)) return;

  const inDaw = !tabStudio.classList.contains("hidden");
  const inVideo = !tabVideo.classList.contains("hidden");
  if (!inDaw && !inVideo) return;

  const getDuration = () => {
    if (inVideo) return vidAudio.duration || 0;
    return dawTracks[0]?.audio?.duration || 0;
  };
  const getCurrent = () => {
    if (inVideo) return vidAudio.currentTime || 0;
    return dawTracks[0]?.audio?.currentTime || 0;
  };
  const seekTo = (t) => {
    const dur = getDuration();
    const clamped = Math.max(0, dur ? Math.min(dur, t) : t);
    if (inVideo) {
      vidAudio.currentTime = clamped;
    } else {
      dawTracks.forEach((trk) => (trk.audio.currentTime = clamped));
    }
  };

  const key = e.key.toLowerCase();
  if (e.code === "Space" || key === "k") {
    e.preventDefault();
    if (inVideo) vidPlayBtn.click();
    else dawPlayBtn.click();
  } else if (e.code === "Escape") {
    e.preventDefault();
    if (inVideo) vidStopBtn.click();
    else dawStopBtn.click();
  } else if (key === "j") {
    e.preventDefault();
    seekTo(getCurrent() - 10);
  } else if (key === "l") {
    e.preventDefault();
    seekTo(getCurrent() + 10);
  } else if (e.code === "ArrowLeft") {
    e.preventDefault();
    seekTo(getCurrent() - 5);
  } else if (e.code === "ArrowRight") {
    e.preventDefault();
    seekTo(getCurrent() + 5);
  } else if (e.key === ",") {
    e.preventDefault();
    seekTo(getCurrent() - 0.1);
  } else if (e.key === ".") {
    e.preventDefault();
    seekTo(getCurrent() + 0.1);
  } else if (e.code === "Home") {
    e.preventDefault();
    seekTo(0);
  } else if (e.code === "End") {
    e.preventDefault();
    seekTo(getDuration());
  } else if (e.code === "ArrowUp") {
    e.preventDefault();
    if (inVideo) {
      vidAudio.volume = Math.min(1, vidAudio.volume + 0.05);
    } else {
      masterGainSlider.value = String(Math.min(150, Number(masterGainSlider.value) + 5));
      updateDspReadouts();
      applyRealtimeDsp();
    }
  } else if (e.code === "ArrowDown") {
    e.preventDefault();
    if (inVideo) {
      vidAudio.volume = Math.max(0, vidAudio.volume - 0.05);
    } else {
      masterGainSlider.value = String(Math.max(0, Number(masterGainSlider.value) - 5));
      updateDspReadouts();
      applyRealtimeDsp();
    }
  } else if (key === "m") {
    e.preventDefault();
    if (inVideo) {
      vidAudio.muted = !vidAudio.muted;
    } else {
      masterGainSlider.value = Number(masterGainSlider.value) > 0 ? "0" : "100";
      updateDspReadouts();
      applyRealtimeDsp();
    }
  } else if (/^[0-9]$/.test(key)) {
    e.preventDefault();
    const dur = getDuration();
    if (dur > 0) seekTo((Number(key) / 10) * dur);
  } else if (key === "t" && inVideo) {
    e.preventDefault();
    vidTapBtn.click();
  }
});

[vidFontSlider, vidDimSlider, vidFadeInSlider, vidFadeOutSlider].forEach((el) => {
  el.addEventListener("input", () => {
    vidFontVal.textContent = vidFontSlider.value;
    vidDimVal.textContent = vidDimSlider.value;
    vidFadeInVal.textContent = vidFadeInSlider.value;
    vidFadeOutVal.textContent = vidFadeOutSlider.value;
  });
});

// Live Video & Fading Lyric Canvas Preview Loop
function drawVideoPreview() {
  requestAnimationFrame(drawVideoPreview);
  if (tabVideo.classList.contains("hidden")) return;

  const ctx = videoPreviewCanvas.getContext("2d");
  const w = videoPreviewCanvas.width;
  const h = videoPreviewCanvas.height;
  ctx.fillStyle = "#08080a";
  ctx.fillRect(0, 0, w, h);

  // Draw Background Photo/GIF/Video (cover crop)
  const src = vidBgKind === "video" && hiddenBgVideo.readyState >= 2 ? hiddenBgVideo : vidBgImage;
  if (src) {
    const sw = src.videoWidth || src.naturalWidth || w;
    const sh = src.videoHeight || src.naturalHeight || h;
    const scale = Math.max(w / sw, h / sh);
    const dw = sw * scale;
    const dh = sh * scale;
    ctx.drawImage(src, (w - dw) / 2, (h - dh) / 2, dw, dh);
  } else {
    ctx.fillStyle = "#555";
    ctx.font = "13px JetBrains Mono, monospace";
    ctx.textAlign = "center";
    ctx.fillText("SELECT PHOTO, GIF, OR VIDEO BACKGROUND", w / 2, h / 2);
  }

  // Background Dim
  const dim = Number(vidDimSlider.value) / 100.0;
  if (dim > 0) {
    ctx.fillStyle = `rgba(0, 0, 0, ${dim})`;
    ctx.fillRect(0, 0, w, h);
  }

  const now = vidAudio.currentTime || 0;
  const fin = Number(vidFadeInSlider.value) / 1000.0;
  const fout = Number(vidFadeOutSlider.value) / 1000.0;
  const fontSize = Math.max(14, Math.round((Number(vidFontSlider.value) / 1080) * h * 1.4));
  const pos = vidPosSelect.value;

  // Intro Title (0.2s - 5.0s)
  const titleText = vidTitleInput.value.trim();
  if (titleText && now >= 0.2 && now <= 5.0) {
    ctx.save();
    ctx.globalAlpha = now < 0.6 ? (now - 0.2) / 0.4 : now > 4.4 ? (5.0 - now) / 0.6 : 1.0;
    ctx.font = `700 ${Math.round(fontSize * 0.72)}px Space Grotesk, sans-serif`;
    ctx.textAlign = "center";
    ctx.fillStyle = vidColorInput.value;
    ctx.shadowColor = "rgba(0,0,0,0.85)";
    ctx.shadowBlur = 8;
    ctx.fillText(titleText, w / 2, h * 0.14);
    ctx.restore();
  }

  // Active Lyric Lines with Fade-In & Fade-Out
  for (const item of vidLyrics) {
    if (!item.text || now < item.start || now > item.end) continue;
    let alpha = 1.0;
    if (fin > 0 && now - item.start < fin) {
      alpha = Math.min(alpha, (now - item.start) / fin);
    }
    if (fout > 0 && item.end - now < fout) {
      alpha = Math.min(alpha, (item.end - now) / fout);
    }
    ctx.save();
    ctx.globalAlpha = Math.max(0, Math.min(1, alpha));
    ctx.font = `700 ${fontSize}px Space Grotesk, sans-serif`;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.lineWidth = 4;
    ctx.strokeStyle = "rgba(0,0,0,0.85)";
    ctx.fillStyle = vidColorInput.value;

    const y = pos === "top" ? h * 0.18 : pos === "center" ? h * 0.5 : h * 0.84;
    ctx.strokeText(item.text, w / 2, y);
    ctx.fillText(item.text, w / 2, y);
    ctx.restore();
  }
}
drawVideoPreview();

async function refreshRenderedVideos() {
  try {
    const res = await fetch("/api/video/files");
    const data = await res.json();
    const videos = data.videos || [];
    if (!videos.length) {
      renderedVideosList.innerHTML = `<div class="empty-state small mono">NO VIDEOS RENDERED YET.</div>`;
      return;
    }
    renderedVideosList.innerHTML = "";
    for (const v of videos) {
      const row = document.createElement("div");
      row.className = "file-item";
      const enc = encodeURIComponent(v.name);
      row.innerHTML = `
        <div class="file-name">${escapeHtml(v.name)} <span class="muted mono small-text">(${formatBytes(v.size)})</span></div>
        <div class="file-actions">
          <a class="btn-link" href="/api/video/files/${enc}" target="_blank">WATCH</a>
          <button type="button" class="ghost-btn vid-save-as-btn">SAVE AS</button>
          <button type="button" class="danger-btn vid-del-btn">DEL</button>
        </div>
      `;
      row.querySelector(".vid-save-as-btn").addEventListener("click", () => {
        saveFileWithPicker(`/api/video/files/${enc}`, v.name);
      });
      row.querySelector(".vid-del-btn").addEventListener("click", async () => {
        await fetch(`/api/video/files/${enc}`, { method: "DELETE" });
        await refreshRenderedVideos();
      });
      renderedVideosList.appendChild(row);
    }
  } catch {
    // ignore
  }
}

refreshVideosBtn.addEventListener("click", refreshRenderedVideos);

renderVideoBtn.addEventListener("click", async () => {
  if (taskBusy) {
    alert("A task is already running. Please wait for it to finish (1 task at a time).");
    return;
  }
  if (!videoMediaSelect.value) {
    alert("Select or upload a photo, GIF, or video background first.");
    return;
  }
  if (!videoAudioSelect.value) {
    alert("Select an audio track first.");
    return;
  }

  const res = await fetch("/api/video/render", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      media_filename: videoMediaSelect.value,
      audio_filename: videoAudioSelect.value,
      output_name: vidOutputName.value.trim() || "Lyric_Video",
      resolution: vidResSelect.value || "1080p",
      lyrics: vidLyrics,
      font_size: Number(vidFontSlider.value),
      text_color: vidColorInput.value,
      outline_color: "#000000",
      position: vidPosSelect.value,
      fade_in_ms: Number(vidFadeInSlider.value),
      fade_out_ms: Number(vidFadeOutSlider.value),
      dim_percent: Number(vidDimSlider.value),
      title_text: vidTitleInput.value.trim() || null,
      save_dir: vidSaveDirInput.value || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    alert(`Video render failed: ${data.detail || "Unknown error"}`);
    return;
  }
  await pollTasks();
});

forwardDawToVideoBtn.addEventListener("click", () => {
  if (lastDawExportedFile) {
    forwardToVideo(lastDawExportedFile);
    return;
  }
  if (dawTracks.some((t) => t.included)) {
    pendingForwardToVideo = true;
    renderMasterBtn.click();
    return;
  }
  if (libraryAddSelect.value) {
    forwardToVideo(libraryAddSelect.value);
    return;
  }
  alert("Load or export a track first to forward to Video Studio.");
});

checkHealth();
loadStudioOptions();
loadVideoOptions();
refreshFiles();
refreshStemSets();
refreshVideoMedia();
refreshRenderedVideos();
pollTasks();
