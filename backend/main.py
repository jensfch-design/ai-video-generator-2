from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-video-generator-2.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VideoRequest(BaseModel):
    prompt: str
    model: str
    duration: int
    aspect: str

@app.get("/healthz")
def health_check():
    return {"status": "ok"}

@app.post("/generate")
def generate_video(data: VideoRequest):
    try:
        print(f"Generating video with prompt: {data.prompt}")
        return {"status": "success", "message": "Video generation started!"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
