/* =============================================
   VOICEDOC — main.js
   Full frontend logic
   ============================================= */

'use strict';

// ─── DOM refs ────────────────────────────────
const themeToggle  = document.getElementById('themeToggle');
const toggleIcon   = document.getElementById('toggleIcon');
const dropZone     = document.getElementById('dropZone');
const fileInput    = document.getElementById('fileInput');
const browseLink   = document.getElementById('browseLink');
const previewArea  = document.getElementById('previewArea');
const previewImg   = document.getElementById('previewImg');
const previewMeta  = document.getElementById('previewMeta');
const removeBtn    = document.getElementById('removeBtn');
const convertBtn   = document.getElementById('convertBtn');
const loadingPanel = document.getElementById('loadingPanel');
const resultPanel  = document.getElementById('resultPanel');
const resultStats  = document.getElementById('resultStats');
const textBox      = document.getElementById('textBox');
const copyBtn      = document.getElementById('copyBtn');
const dlMp3        = document.getElementById('dlMp3');
const dlTxt        = document.getElementById('dlTxt');
const toastContainer = document.getElementById('toastContainer');

// Step elements
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');

// Audio player
const audioEl       = document.getElementById('audioEl');
const playPauseBtn  = document.getElementById('playPauseBtn');
const playIcon      = playPauseBtn.querySelector('.play-icon');
const pauseIcon     = playPauseBtn.querySelector('.pause-icon');
const seekbar       = document.getElementById('seekbar');
const timeDisplay   = document.getElementById('timeDisplay');
const speedSelect   = document.getElementById('speedSelect');
const volumeSlider  = document.getElementById('volumeSlider');
const volIcon       = document.getElementById('volIcon');

// ─── State ───────────────────────────────────
let selectedFile   = null;
let currentAudioUrl = null;
let extractedText  = '';
let stepTimers     = [];

// ─── Dark Mode ───────────────────────────────
(function initTheme() {
  const saved = localStorage.getItem('voicedoc-theme') || 'dark';
  applyTheme(saved);
})();

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  toggleIcon.textContent = theme === 'dark' ? '☀️' : '🌙';
  localStorage.setItem('voicedoc-theme', theme);
}

themeToggle.addEventListener('click', () => {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
});

// ─── Drag and Drop ───────────────────────────
dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', (e) => {
  if (!dropZone.contains(e.relatedTarget)) {
    dropZone.classList.remove('drag-over');
  }
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

// Click to browse
browseLink.addEventListener('click', (e) => {
  e.stopPropagation();
  fileInput.click();
});

dropZone.addEventListener('click', () => {
  fileInput.click();
});

// Keyboard: Enter on drop zone
dropZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    fileInput.click();
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

// Remove file
removeBtn.addEventListener('click', () => {
  resetFile();
});

// ─── File Handling ───────────────────────────
function handleFile(file) {
  const allowed = ['image/jpeg', 'image/png', 'image/bmp'];
  if (!allowed.includes(file.type)) {
    showToast('Please upload a JPG, PNG, or BMP image.', 'error');
    return;
  }

  if (file.size > 20 * 1024 * 1024) {
    showToast('File too large. Max 20 MB.', 'error');
    return;
  }

  selectedFile = file;

  // Image preview
  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    previewMeta.innerHTML =
      `<strong>${escapeHtml(file.name)}</strong><br>` +
      `${(file.size / 1024).toFixed(1)} KB · ${file.type.split('/')[1].toUpperCase()}`;
  };
  reader.readAsDataURL(file);

  previewArea.hidden = false;
  convertBtn.disabled = false;
}

function resetFile() {
  selectedFile = null;
  fileInput.value = '';
  previewArea.hidden = true;
  previewImg.src = '';
  convertBtn.disabled = true;
}

// ─── Convert ─────────────────────────────────
convertBtn.addEventListener('click', () => {
  if (!selectedFile) return;
  startConversion();
});

async function startConversion() {
  // Reset previous results
  resultPanel.hidden = true;
  audioEl.src = '';
  currentAudioUrl = null;
  extractedText = '';

  // Show loading
  loadingPanel.hidden = false;
  convertBtn.disabled = true;
  convertBtn.querySelector('.btn-text').textContent = 'Converting…';

  // Animated steps
  resetSteps();
  activateStep(step1, null);

  stepTimers.push(setTimeout(() => {
    doneStep(step1, document.querySelector('#step1 + .step-connector'));
    activateStep(step2, null);
  }, 1500));

  stepTimers.push(setTimeout(() => {
    doneStep(step2, document.querySelector('#step2 + .step-connector'));
    activateStep(step3, null);
  }, 3000));

  // Actual API call
  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const response = await fetch('/convert', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    // Clear step timers
    stepTimers.forEach(clearTimeout);
    stepTimers = [];

    if (data.success) {
      // Mark all done
      doneStep(step1, document.querySelector('#step1 + .step-connector'));
      doneStep(step2, document.querySelector('#step2 + .step-connector'));
      doneStep(step3, null);

      setTimeout(() => {
        loadingPanel.hidden = true;
        showResults(data);
      }, 600);
    } else {
      loadingPanel.hidden = true;
      showToast(data.error || 'Conversion failed.', 'error');
      resetConvertBtn();
    }
  } catch (err) {
    stepTimers.forEach(clearTimeout);
    stepTimers = [];
    loadingPanel.hidden = true;
    showToast('Network error. Is the server running?', 'error');
    resetConvertBtn();
  }
}

function resetConvertBtn() {
  convertBtn.disabled = false;
  convertBtn.querySelector('.btn-text').textContent = 'Convert to Speech';
}

// ─── Steps ───────────────────────────────────
function resetSteps() {
  [step1, step2, step3].forEach(s => {
    s.className = 'step-item pending';
  });
  document.querySelectorAll('.step-connector').forEach(c => {
    c.classList.remove('done');
  });
}

function activateStep(stepEl) {
  stepEl.className = 'step-item active';
}

function doneStep(stepEl, connectorEl) {
  stepEl.className = 'step-item done';
  if (connectorEl) connectorEl.classList.add('done');
}

// ─── Show Results ─────────────────────────────
function showResults(data) {
  extractedText = data.text;
  currentAudioUrl = data.audio_url;

  // Stats
  resultStats.innerHTML = `
    <span class="stat-chip">📝 ${data.word_count} words</span>
    <span class="stat-chip">🔤 ${data.char_count} chars</span>
  `;

  // Text
  textBox.textContent = data.text;

  // Audio
  audioEl.src = data.audio_url;
  audioEl.load();
  updateSeekbarFill(0);

  // Show panel
  resultPanel.hidden = false;
  resultPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  showToast('Conversion complete! 🎉', 'success');
  resetConvertBtn();
}

// ─── Copy Button ─────────────────────────────
copyBtn.addEventListener('click', () => {
  if (!extractedText) return;
  navigator.clipboard.writeText(extractedText).then(() => {
    copyBtn.textContent = '✓ Copied!';
    showToast('Text copied to clipboard!', 'success');
    setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
  }).catch(() => {
    // Fallback for older browsers
    const ta = document.createElement('textarea');
    ta.value = extractedText;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    copyBtn.textContent = '✓ Copied!';
    showToast('Text copied to clipboard!', 'success');
    setTimeout(() => { copyBtn.textContent = '📋 Copy'; }, 2000);
  });
});

// ─── Download MP3 ────────────────────────────
dlMp3.addEventListener('click', () => {
  if (!currentAudioUrl) return;
  const a = document.createElement('a');
  a.href = currentAudioUrl;
  a.download = 'voicedoc-output.mp3';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast('Downloading MP3…', 'info');
});

// ─── Download TXT ────────────────────────────
dlTxt.addEventListener('click', () => {
  if (!extractedText) return;
  const blob = new Blob([extractedText], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'voicedoc-output.txt';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('Downloading TXT…', 'info');
});

// ─── Custom Audio Player ─────────────────────
playPauseBtn.addEventListener('click', () => {
  if (audioEl.paused) {
    audioEl.play().catch(e => showToast('Audio play failed: ' + e.message, 'error'));
  } else {
    audioEl.pause();
  }
});

audioEl.addEventListener('play', () => {
  playIcon.hidden = true;
  pauseIcon.hidden = false;
});

audioEl.addEventListener('pause', () => {
  playIcon.hidden = false;
  pauseIcon.hidden = true;
});

audioEl.addEventListener('ended', () => {
  playIcon.hidden = false;
  pauseIcon.hidden = true;
  seekbar.value = 0;
  updateSeekbarFill(0);
});

audioEl.addEventListener('timeupdate', () => {
  if (!audioEl.duration) return;
  const pct = (audioEl.currentTime / audioEl.duration) * 100;
  seekbar.value = pct;
  updateSeekbarFill(pct);
  timeDisplay.textContent = `${formatTime(audioEl.currentTime)} / ${formatTime(audioEl.duration)}`;
});

audioEl.addEventListener('loadedmetadata', () => {
  seekbar.max = 100;
  timeDisplay.textContent = `0:00 / ${formatTime(audioEl.duration)}`;
});

seekbar.addEventListener('input', () => {
  if (!audioEl.duration) return;
  const t = (seekbar.value / 100) * audioEl.duration;
  audioEl.currentTime = t;
  updateSeekbarFill(parseFloat(seekbar.value));
});

speedSelect.addEventListener('change', () => {
  audioEl.playbackRate = parseFloat(speedSelect.value);
});

volumeSlider.addEventListener('input', () => {
  const vol = volumeSlider.value / 100;
  audioEl.volume = vol;
  if (vol === 0) volIcon.textContent = '🔇';
  else if (vol < 0.5) volIcon.textContent = '🔉';
  else volIcon.textContent = '🔊';
});

volIcon.addEventListener('click', () => {
  if (audioEl.volume > 0) {
    audioEl.volume = 0;
    volumeSlider.value = 0;
    volIcon.textContent = '🔇';
  } else {
    audioEl.volume = 1;
    volumeSlider.value = 100;
    volIcon.textContent = '🔊';
  }
});

function updateSeekbarFill(pct) {
  seekbar.style.background =
    `linear-gradient(to right, var(--accent-purple) 0%, var(--accent-teal) ${pct}%, var(--glass-border) ${pct}%)`;
}

function formatTime(secs) {
  if (isNaN(secs)) return '0:00';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ─── Toast Notifications ─────────────────────
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;

  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${escapeHtml(message)}</span>`;

  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => {
      if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 300);
  }, 3500);
}

// ─── Utility ─────────────────────────────────
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
