// ---- CONFIG ----
// Your Render backend:
const API_BASE = 'https://ai-video-generator-2-wmts.onrender.com';

// ---- ELEMENTS ----
const els = {
  prompt: document.getElementById('prompt'),
  model: document.getElementById('model'),
  duration: document.getElementById('duration'),
  aspect: document.getElementById('aspect'),
  goBtn: document.getElementById('goBtn'),
  video: document.getElementById('video'),
  status: document.getElementById('status'),
};

// ---- LOGGING ----
function log(msg) {
  console.log(msg);
  if (els.status) {
    els.status.textContent = typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2);
  }
}

// ---- HEALTH CHECK ----
async function healthCheck() {
  try {
    const res = await fetch(`${API_BASE}/healthz`);
    const json = await res.json();
    log(`✅ Health OK: ${JSON.stringify(json)}`);
  } catch (err) {
    log(`❌ Health check failed: ${err.message}`);
  }
}

// ---- GENERATE VIDEO ----
async function generate() {
  const payload = {
    prompt: els.prompt?.value || '',
    model: els.model?.value || 'cinematic',
    duration: Number(els.duration?.value) || 5,
    aspect: els.aspect?.value || '16:9',
  };

  log('Generating video...');
  try {
    const res = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const json = await res.json();
    log(json);

    if (json.video_url && els.video) {
      els.video.src = json.video_url;
      els.video.classList.remove('hidden');
      els.video.load();
    }
  } catch (err) {
    log(`⚠️ Error: ${err.message}`);
  }
}

// ---- WIRE BUTTON ----
document.addEventListener('DOMContentLoaded', () => {
  console.log('JS loaded, wiring button...');
  if (els.goBtn) {
    els.goBtn.addEventListener('click', generate);
    console.log('Button wired!');
  } else {
    console.error('⚠️ goBtn not found in DOM!');
  }

  // Test backend connection when page loads
  healthCheck();
});

