from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import HTMLResponse

app = FastAPI()

# Allow your deployed frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
)

class VideoRequest(BaseModel):
    prompt: str
    model: str | None = None
    duration: int | None = None
    aspect: str | None = None

@app.get("/", response_class=HTMLResponse)
def home():
    return """<h1>AI Video Generator API</h1>
<p>✅ Server is running</p>
<p>Health check: <a href="/healthz">/healthz</a></p>"""

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/generate")
def generate_video(data: VideoRequest):
    print(f"Generating video with prompt: {data.prompt}")
    # Just return a fake response for now so frontend resolves it
    return {
    "status": "queued",
    "message": f"Video generation started for: {data.prompt}",
    "video_url": "https://sample-videos.com/video321/mp4/720/big_buck_bunny_720p_1mb.mp4",
    "echo": data.model_dump(),
}

    }
