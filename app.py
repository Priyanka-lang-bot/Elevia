"""ELEVIA web entry point (Vercel and local).

- /api/...  → the FastAPI backend (backend/main.py)
- /...      → the website in public/ (Vercel serves it from its CDN; locally we serve it here)

Run locally:  python -m uvicorn app:app --reload   then open http://localhost:8000
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from backend.main import app as api
from backend.main import startup


@asynccontextmanager
async def lifespan(_: FastAPI):
    startup()  # mounted sub-apps don't run their own startup, so do it here
    yield


app = FastAPI(title="ELEVIA", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)


@app.get("/", include_in_schema=False)
def home(request: Request):
    # keep ?action=...&token=... from email links
    q = request.url.query
    return RedirectResponse("/index.html" + (f"?{q}" if q else ""), status_code=307)


if not os.getenv("VERCEL"):  # on Vercel, public/ is served by the platform; don't mount it there
    from fastapi.staticfiles import StaticFiles
    app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent / "public", html=True), name="web")
