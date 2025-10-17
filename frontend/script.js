// --- CONFIG ---
// Your Render backend:
const API_BASE = 'https://ai-video-generator-2-wmts.onrender.com';

const els = {
  prompt:  document.getElementById('prompt'),
  model:   document.getElementById('model'),
  duration:document.getElementById('duration'),
  aspect:  document.getElementById('aspect'),
  goBtn:   document.getElementById('goBtn') || document.querySelector('button[type="button"], button'),
  video:   document.getElementById('preview'),
  log:     document.getElementById('log')
};

function log(msg) {
  if (!els.log) return;
  els.log.textContent += (typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2)) + '\n';
  els.log.scrollTop = els.log.scrollHeight;
}

async function healthCheck() {
  try {
    const r = await fetch(`${API_BASE}/healthz`);
    const j = await r.json();
    log('Health: ' + JSON.stringify(j));
  } catch (e) {
    log('Health check failed: ' + e.message);
  }
}

async function generate() {
  const payload = {
    prompt:  (els.prompt?.value || '').trim(),
    model:   els.model?.value || 'cinematic',
    duration: Number(els.duration?.value || 5),
    aspect:  els.aspect?.value || '16:9'
  };

  if (!payload.prompt) {
    alert('Please write a prompt first 🙂');
    return;
  }

  els.goBtn?.setAttribute('disabled', 'true');
  els.goBtn && (els.goBtn.textContent = 'Working…');

  log('Sending /generate payload:');
  log(payload);

  try {
    const r = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await r.json().catch(() => ({}));
    log('Response:');
    log(data);

    if (!r.ok) {
      alert(`Server error: ${r.status} ${r.statusText}`);
      return;
    }

    // If your backend later returns a video URL, set it here:
    // if (data.video_url && els.video) {
    //   els.video.src = data.video_url;
    //   els.video.load();
    //   els.video.play().catch(() => {});
    // } else {
    //   log('No video_url yet (placeholder response).');
    // }
  } catch (e) {
    log('Request failed: ' + e.message);
    alert('Could not reach the backend. Check CORS/URL and try again.');
  } finally {
    els.goBtn?.removeAttribute('disabled');
    els.goBtn && (els.goBtn.textContent = 'Generate Video');
  }
}

// Wire up
if (els.goBtn) els.goBtn.addEventListener('click', generate);
// optional: ping health on load
healthCheck();

