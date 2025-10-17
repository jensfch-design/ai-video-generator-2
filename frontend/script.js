// Set your backend API. You can override this via DevTools with:
// localStorage.setItem('API_BASE','https://YOUR-RENDER.onrender.com');
const API_BASE =
  localStorage.getItem('API_BASE') ||
  'https://ai-video-generator-2-wmts.onrender.com';

const $ = (id) => document.getElementById(id);
const statusEl = $('status');
const videoEl = $('video');
const btn = $('btn');

function setStatus(text) {
  statusEl.textContent = text;
}

btn.addEventListener('click', async () => {
  const payload = {
    prompt: $('prompt').value.trim(),
    model: $('model').value,
    duration_seconds: parseInt($('duration').value || '5', 10),
    aspect_ratio: $('aspect').value,
  };

  if (!payload.prompt) {
    alert('Skriv inn en prompt først 🙏');
    return;
  }

  // reset UI
  setStatus('Sender forespørsel…');
  videoEl.classList.add('hidden');
  videoEl.src = '';

  try {
    const res = await fetch(`${API_BASE}/generate`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');

    // Poll status until done
    await pollStatus(data.job_id);
  } catch (err) {
    console.error(err);
    setStatus('Feil: ' + (err?.message || 'Ukjent feil'));
  }
});

async function pollStatus(jobId) {
  setStatus('Køet…');
  for (let i = 0; i < 60; i++) {
    const res = await fetch(`${API_BASE}/status/${jobId}`);
    const data = await res.json();

    if (data.status === 'succeeded') {
      setStatus('Ferdig! ▶️');
      if (data.video_url) {
        videoEl.src = data.video_url;
        videoEl.classList.remove('hidden');
        try { await videoEl.play(); } catch (_) {}
      }
      return;
    }
    if (data.status === 'failed') {
      setStatus('Feilet: ' + (data.error || 'Ukjent feil'));
      return;
    }

    setStatus(`Status: ${data.status} …`);
    await new Promise((r) => setTimeout(r, 1000));
  }
  setStatus('Tidsavbrudd etter 60 sek.');
}
