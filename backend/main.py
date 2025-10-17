# backend/main.py
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import os, time
import httpx

app = FastAPI()

# --- CORS: allow your deployed Vercel domains ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-video-generator-2.vercel.app",
        # Optional – preview deployments:
        "https://ai-video-generator-2-git-main-jens-projects-0278bd39.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- Provider adapter (fill with your real provider) --------
PROVIDER = os.getenv("VIDEO_PROVIDER", "demo")  # "demo" (sample), or "custom"
PROVIDER_API_KEY = os.getenv("VIDEO_API_KEY", "")       # put real key in Render
PROVIDER_BASE_URL = os.getenv("VIDEO_API_BASE", "")     # put real base URL in Render

# Example shapes (these are placeholders so you can map to your provider):
# - Create job:  POST {PROVIDER_BASE_URL}/v1/videos  -> { "id": "job_123" }
# - Get status:  GET  {PROVIDER_BASE_URL}/v1/videos/{id} -> 
#       { "status": "succeeded"|"queued"|"running"|"failed", "assets": { "video": "https://..." } }


class VideoRequest(BaseModel):
    prompt: str
    model: str | None = None
    duration: int | None = 5
    aspect: str | None = "16:9"


def _demo_response(data: VideoRequest) -> dict:
    """Fallback demo result with a public sample clip."""
    return {
        "status": "queued",
        "message": f"Video generation started for: {data.prompt}",
        "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
        "echo": data.model_dump(),
    }


async def _provider_create_job(client: httpx.AsyncClient, req: VideoRequest) -> dict:
    """
    Create a job with your provider. Replace JSON body/headers/endpoint
    with the values required by your subscription.
    """
    if not (PROVIDER_API_KEY and PROVIDER_BASE_URL):
        # No real provider configured
        return {"demo": True}

    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": req.prompt,
        # map your provider’s params here:
        "duration": req.duration or 5,
        "aspect_ratio": req.aspect or "16:9",
        "model": req.model or "cinematic",
    }

    # >>> Replace this with your provider's create endpoint
    create_url = f"{PROVIDER_BASE_URL.rstrip('/')}/v1/videos"

    r = await client.post(create_url, json=payload, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()
    # Make sure to return the job id key the provider uses:
    job_id = data.get("id") or data.get("job_id")
    return {"job_id": job_id, "raw": data}


async def _provider_get_status(client: httpx.AsyncClient, job_id: str) -> dict:
    """
    Poll job status. Replace endpoint/field names per your provider.
    Must return:
      - status: "succeeded"|"queued"|"running"|"failed"
      - video_url: str|None
    """
    headers = {
        "Authorization": f"Bearer {PROVIDER_API_KEY}",
    }
    # >>> Replace with your provider's status endpoint
    status_url = f"{PROVIDER_BASE_URL.rstrip('/')}/v1/videos/{job_id}"

    r = await client.get(status_url, headers=headers, timeout=60)
    r.raise_for_status()
    data = r.json()

    status = data.get("status", "queued")
    # adjust path to video URL per provider
    video_url = (data.get("assets") or {}).get("video") or data.get("video_url")

    return {"status": status, "video_url": video_url, "raw": data}


async def _try_generate_real_video(req: VideoRequest, max_wait_sec: int = 60, poll_every: float = 3.0) -> dict:
    """
    If provider is configured, create job and poll up to max_wait_sec.
    If finished, return video_url. Otherwise return queued + job_id.
    """
    async with httpx.AsyncClient() as client:
        # 1) Create job
        created = await _provider_create_job(client, req)
        if created.get("demo"):
            # No provider configured -> fall back to demo response
            return _demo_response(req)

        job_id = created.get("job_id")
        if not job_id:
            return {"status": "error", "message": "Provider did not return a job id.", "echo": created}

        # 2) Poll for completion (up to max_wait_sec)
        start = time.time()
        while time.time() - start < max_wait_sec:
            status = await _provider_get_status(client, job_id)
            st = status.get("status", "queued")
            vurl = status.get("video_url")

            if st in ("succeeded", "completed") and vurl:
                return {"status": "succeeded", "video_url": vurl, "job_id": job_id}

            if st in ("failed", "error"):
                return {"status": "failed", "message": "Generation failed.", "job_id": job_id, "echo": status}

            await asyncio_sleep(poll_every)

        # Not ready yet -> let frontend poll later
        return {"status": "queued", "job_id": job_id, "message": "Still processing, check back soon."}


# small awaitable sleep helper (works without importing asyncio at top-level)
import asyncio
async def asyncio_sleep(s: float):
    await asyncio.sleep(s)

# ---------------- Routes ----------------

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
    try:
        # If you want to force demo while you test, set VIDEO_PROVIDER=demo in Render
        if PROVIDER == "demo":
            return JSONResponse(_demo_response(data))

        # Else attempt the real provider flow
        result = await _try_generate_real_video(data)
        return JSONResponse(result)

    except httpx.HTTPStatusError as e:
        return JSONResponse({"status": "error", "message": f"Provider HTTP {e.response.status_code}", "detail": e.response.text}, status_code=502)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)

@app.get("/result")
async def get_result(job_id: str = Query(..., description="Job id to check")):
    if PROVIDER == "demo":
        # Nothing to check in demo mode
        return {"status": "succeeded", "video_url": _demo_response(VideoRequest(prompt='demo'))["video_url"]}

    if not (PROVIDER_API_KEY and PROVIDER_BASE_URL):
        return {"status": "error", "message": "Provider not configured."}

    try:
        async with httpx.AsyncClient() as client:
            status = await _provider_get_status(client, job_id)
        st = status.get("status", "queued")
        vurl = status.get("video_url")
        if st in ("succeeded", "completed") and vurl:
            return {"status": "succeeded", "video_url": vurl}
        elif st in ("failed", "error"):
            return {"status": "failed", "message": "Generation failed."}
        else:
            return {"status": "queued", "job_id": job_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}
