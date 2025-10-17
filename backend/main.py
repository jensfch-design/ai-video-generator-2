# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os, time, httpx

app = FastAPI()

# --- CORS: allow your Vercel domains ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-video-generator-2.vercel.app",
        # optional: your preview deploys on vercel
        "https://ai-video-generator-2-git-main-jens-projects-0278bd39.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Provider settings via ENV ---
PROVIDER       = os.getenv("VIDEO_PROVIDER", "sora")  # "sora" by default
PROVIDER_BASE  = os.getenv("VIDEO_API_BASE", "").rstrip("/")
PROVIDER_KEY   = os.getenv("VIDEO_API_KEY", "")

# Basic “shape” so you can adapt easily if your provider differs:
# Create job:   POST  {PROVIDER_BASE}/v1/videos
#   -> payload: {prompt, model?, duration?, aspect?}
#   -> returns: {"id": "...", "status": "...", ...}
# Get status:   GET   {PROVIDER_BASE}/v1/videos/{id}
#   -> returns: {"status": "succeeded|running|queued|failed", "assets": [{"url": "...", "type": "video"}]} or {"output":{"url": "..."}}

# --- Request schema from your frontend ---
class VideoRequest(BaseModel):
    prompt: str
    model: str | None = None
    duration: int | None = 5
    aspect: str | None = "16:9"

@app.get("/", response_class=HTMLResponse)
def home():
    return """<h1>AI Video Generator API</h1>
<p>✅ Server is running</p>
<p>Health check: <a href="/healthz">/healthz</a></p>"""

@app.get("/healthz")
def health_check():
    ok = bool(PROVIDER_BASE and PROVIDER_KEY)
    return {"status": "ok" if ok else "missing_env", "provider": PROVIDER}

def aspect_to_size(aspect: str | None) -> str:
    """
    Map aspect to the provider's size field if needed.
    Adjust to match your provider's accepted sizes.
    """
    if not aspect:
        return "1280x720"
    a = aspect.replace(" ", "")
    return {
        "16:9": "1280x720",
        "9:16": "720x1280",
        "1:1":  "1024x1024",
    }.get(a, "1280x720")

@app.post("/generate")
async def generate_video(data: VideoRequest):
    if not (PROVIDER_BASE and PROVIDER_KEY):
        return JSONResponse(
            {"status": "error", "message": "Server missing VIDEO_API_BASE or VIDEO_API_KEY"},
            status_code=500,
        )

    # ---- 1) Create the job at the provider ----
    create_url = f"{PROVIDER_BASE}/v1/videos"

    # ✳️ Adjust this mapping to your provider’s exact field names if needed
    payload = {
        "prompt": data.prompt,
        "model": data.model or "cinematic",
        "duration": data.duration or 5,
        "size": aspect_to_size(data.aspect),     # some APIs use "size" or "resolution"
        # add any other provider-specific options here
    }

    headers = {
        "Authorization": f"Bearer {PROVIDER_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        try:
            create = await client.post(create_url, json=payload, headers=headers)
        except Exception as e:
            return {"status": "error", "message": f"Create request failed: {e}"}

    if create.status_code >= 300:
        return {
            "status": "error",
            "message": f"Create failed: {create.status_code}",
            "detail": create.text,
        }

    job = create.json()
    job_id = job.get("id") or job.get("job_id")

    # If the provider returns the URL immediately, surface it:
    video_url = (
        job.get("video_url")
        or (job.get("output") or {}).get("url")
        or (next((a.get("url") for a in job.get("assets", []) if a.get("url")), None))
    )
    if video_url:
        return {"status": "succeeded", "video_url": video_url, "echo": data.model_dump()}

    if not job_id:
        return {"status": "queued", "message": "Job created but no id in response", "raw": job}

    # ---- 2) Poll for result (short window; frontend can display queued state) ----
    status_url = f"{PROVIDER_BASE}/v1/videos/{job_id}"
    deadline = time.time() + 75  # ~75 seconds poll window
    last_status = None

    while time.time() < deadline:
        await asyncio_sleep(3.0)
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                status_res = await client.get(status_url, headers=headers)
            except Exception as e:
                last_status = f"poll_error: {e}"
                continue

        if status_res.status_code >= 300:
            last_status = f"poll_http_{status_res.status_code}"
            continue

        s = status_res.json()
        state = s.get("status") or s.get("state")
        # Locate a URL in common shapes
        video_url = (
            s.get("video_url")
            or (s.get("output") or {}).get("url")
            or (next((a.get("url") for a in s.get("assets", []) if a.get("url")), None))
        )

        if state in ("succeeded", "completed") and video_url:
            return {"status": "succeeded", "video_url": video_url, "echo": data.model_dump()}
        if state in ("failed", "canceled", "error"):
            return {"status": "error", "message": f"Job {state}", "raw": s}

        # still running / queued
        last_status = state or "running"

    # Timed out waiting—let the frontend keep showing queued state if you want
    return {"status": "queued", "message": f"Still running ({last_status})", "id": job_id, "echo": data.model_dump()}


# tiny async sleep helper (so we can use it without bringing in asyncio everywhere)
import asyncio
async def asyncio_sleep(sec: float):
    await asyncio.sleep(sec)

