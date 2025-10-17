# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os, requests, json

app = FastAPI()

# ---- Allow your frontend to connect ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-video-generator-2.vercel.app",
        "https://ai-video-generator-2-git-main-jens-projects-0278bd39.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Environment variables (from Render dashboard) ----
PROVIDER = os.getenv("VIDEO_PROVIDER", "sora")
PROVIDER_BASE = os.getenv("VIDEO_API_BASE", "https://api.openai.com/v1")
PROVIDER_KEY = os.getenv("VIDEO_API_KEY", "")

# ---- Request model from frontend ----
class VideoRequest(BaseModel):
    prompt: str
    model: str | None = "gpt-4o-video-preview"
    duration: int | None = 5
    aspect: str | None = "16:9"


# ---- Root and health check ----
@app.get("/", response_class=HTMLResponse)
def home():
    return """<h1>AI Video Generator API</h1><p>Server running ✅</p><p><a href='/healthz'>Health check</a></p>"""


@app.get("/healthz")
def health_check():
    return {"status": "ok", "provider": PROVIDER}


# ---- Generate video using OpenAI Sora ----
@app.post("/generate")
def generate_video(data: VideoRequest):
    """
    Generate a video using the OpenAI (Sora) API.
    """
    headers = {
        "Authorization": f"Bearer {PROVIDER_KEY}",
        "Content-Type": "application/json",
    }

    create_url = f"{PROVIDER_BASE}/videos"

    payload = {
        "model": "gpt-4o-video-preview",  # Sora video model
        "prompt": data.prompt,
        "duration": data.duration,
        "aspect_ratio": data.aspect or "16:9",
    }

    print(f"➡️ Sending to {create_url}: {payload}")

    try:
        response = requests.post(create_url, headers=headers, json=payload, timeout=60)
        result = response.json()
        print("✅ Sora API response:", result)

        return {
            "status": result.get("status", "queued"),
            "message": f"Video generation started for: {data.prompt}",
            "video_url": result.get("video_url"),
            "api_response": result,
        }

    except Exception as e:
        print("❌ Error generating video:", e)
        return {"status": "error", "message": str(e)}


# ---- Optional helper (for async sleep etc.) ----
import asyncio
async def asyncio_sleep(sec: float):
    await asyncio.sleep(sec)


