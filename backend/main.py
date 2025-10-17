from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
def home():
    return """<h1>AI Video Generator API</h1>
              <p>Server is running ✅</p>
              <p>Health check: <a href='/healthz'>/healthz</a></p>"""

@app.get("/healthz")
def healthz():
    return {"ok": True}
