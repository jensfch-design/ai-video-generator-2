# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os
import httpx

app = FastAPI()

# --- CORS: allow your deployed Vercel domains ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-video-generator-2.vercel.app",
        # optional: your Vercel preview domain (copy/paste exactly as shown by Vercel)
        "https://ai-video-generator-2-git-main-jens-projects-0278bd39.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Provider adapter (fill with your real provider) --------
PROVIDER = os.getenv("VIDEO_PROVIDER", "demo")         # "demo" by default
PROVIDER_API_KEY = os.getenv("VIDEO_API_KEY", "")      # set in Render if needed
PROVIDER_BASE_URL = os.getenv("VIDEO_API_BASE", "")    # set in Render if needed

class VideoRequest(BaseModel):
    prompt: str
    model: str | None = None
    duration: int | None = None
    aspect: str | None = "16:9"

@app.get("/", response_class=HTMLResponse)
def home():
    return """<h1>AI Video Generator API</h1>
<p>✅ Server is running</p>
<p>Health check: <a href="/healthz">/healthz</a></p>"""

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/generate")
async def generate_video(data: VideoRequest):
    """
    Returns either:
    - demo: a sample video URL (so your app works now)
    - provider: placeholder logic for a real provider (wire later)
    """
    # DEMO mode: return a known-public sample video so the frontend can play
    if PROVIDER.lower() in ("", "demo", "sample"):
        return {
            "status": "queued",
            "message": f"Video generation started for: {data.prompt}",
            "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
            "echo": data.model_dump(),
        }

    # REAL PROVIDER (skeleton): adapt to your provider’s API when you’re ready.
    # Example pattern: POST job -> get job_id -> poll until 'succeeded' -> return asset link
    if not PROVIDER_BASE_URL:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Provider base URL not configured"},
        )

    headers = {}
    if PROVIDER_API_KEY:
        headers["Authorization"] = f"Bearer {PROVIDER_API_KEY}"

    payload = {
        "prompt": data.prompt,
        "model": data.model or "cinematic",
        "duration": data.duration or 5,
        "aspect": data.aspect or "16:9",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        # 1) create a job
        create = await client.post(f"{PROVIDER_BASE_URL}/v1/videos", json=payload, headers=headers)
        if create.status_code >= 400:
            return JSONResponse(status_code=create.status_code, content=create.json())

        job = create.json()
        job_id = job.get("id") or job.get("job_id") or job.get("data", {}).get("id")
        if not job_id:
            return JSONResponse(status_code=500, content={"status": "error", "message": "No job id from provider"})

        # 2) (simplified) poll a few times for demo purposes
        for _ in range(15):
            status_res = await client.get(f"{PROVIDER_BASE_URL}/v1/videos/{job_id}", headers=headers)
            if status_res.status_code >= 400:
                return JSONResponse(status_code=status_res.status_code, content=status_res.json())
            sjson = status_res.json()
            st = sjson.get("status")
            if st in ("succeeded", "completed"):
                # adapt path to your provider’s response
                vid = (
                    sjson.get("assets", {}).get("video")
                    or sjson.get("video_url")
                    or sjson.get("result", {}).get("url")
                )
                if vid:
                    return {"status": "succeeded", "video_url": vid, "provider": PROVIDER, "echo": payload}
                return JSONResponse(status_code=500, content={"status": "error", "message": "No video URL in success response"})
            elif st in ("failed", "error"):
                return JSONResponse(status_code=500, content={"status": "failed", "detail": sjson})
            # brief wait between polls
            import asyncio; await asyncio.sleep(2)

    return JSONResponse(status_code=504, content={"status": "timeout", "message": "Provider did not finish in time"})

