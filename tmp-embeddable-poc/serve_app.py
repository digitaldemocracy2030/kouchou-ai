import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok", "executable": sys.executable}

# Validate the "FastAPI serves Next static export" idea
app.mount("/", StaticFiles(directory="webroot", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8123, log_level="warning")
