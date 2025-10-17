from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- CORS setup ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-video-generator-2.vercel.app",  # your Vercel domain
        "http://localhost:3000",                    # optional, for local testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Root route ---
@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <h1>AI Video Generator API</h1>
    <p>Server is running ✅</p>
    <p>Health check: <a href="/healthz">/healthz</a></p>
    """

# --- Health check ---
@app.get("/healthz")
def healthz():
    return {"ok": True}
