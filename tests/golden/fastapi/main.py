import json
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

from config.settings import settings
from core.errors import register_error_handlers
from database import engine
from routers.auth import router as auth_router
from routers.user import router as user_router

PROJECT = {
    "project": 'GoldenAPI',
    "target": 'FASTAPI',
    "semarc_version": '0.14.0',
    "models": ['User'],
    "routes": ['GET /', 'GET /health', 'GET /routes', 'GET /openapi.json', 'GET /docs', 'POST /login', 'GET /users', 'POST /register', 'GET /me'],
}

OPENAPI_DOCUMENT = json.loads((Path(__file__).resolve().parent / "openapi.json").read_text(encoding="utf-8"))

app = FastAPI(title=PROJECT["project"], version="0.1.0")
app.openapi = lambda: OPENAPI_DOCUMENT  # the SEMARC contract, shared by every target
register_error_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    models = "".join(f"<li>{escape(model)}</li>" for model in PROJECT["models"])
    routes = "".join(f"<li>{escape(route)}</li>" for route in PROJECT["routes"])
    return (
        f"<!doctype html><html><head><meta charset=\"utf-8\"><title>{escape(PROJECT['project'])}</title></head><body>"
        "<h1>SEMARC Generated Project</h1>"
        f"<p><strong>Project:</strong> {escape(PROJECT['project'])}</p>"
        f"<p><strong>Target:</strong> {PROJECT['target']}</p>"
        f"<p><strong>SEMARC Version:</strong> {PROJECT['semarc_version']}</p>"
        f"<h2>Models</h2><ul>{models}</ul><h2>Routes</h2><ul>{routes}</ul>"
        "<p><strong>Status:</strong> Running</p></body></html>"
    )


@app.get("/health")
def health() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "ok"
    except Exception:
        database = "unavailable"
    status = "ok" if database == "ok" else "degraded"
    return JSONResponse(
        {"status": status, "project": PROJECT["project"], "database": database},
        status_code=200 if database == "ok" else 503,
    )


@app.get("/routes")
def routes() -> dict:
    return {"routes": PROJECT["routes"]}


app.include_router(auth_router)
app.include_router(user_router)
