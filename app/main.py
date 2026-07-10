from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.routers import audit, documents

app = FastAPI(title="doc-share")

app.include_router(documents.router)
app.include_router(audit.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/upload.html")


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
