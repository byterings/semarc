from fastapi import FastAPI

from middleware.token_validation_middleware import TokenValidationMiddleware
from config.settings import settings
from routers.auth import router as auth_router
from routers.user import router as user_router

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(TokenValidationMiddleware)
app.include_router(auth_router)
app.include_router(user_router)


@app.get("/")
def home():
    return {
        "title": "SEMARC Generated Project",
        "project": "GoldenAPI",
        "target": "FastAPI",
        "semarc_version": "0.13.0",
        "models": ['User'],
        "routes": ['GET /', 'GET /health', 'GET /routes', 'POST /login', 'GET /users'],
        "profiles": [],
        "modules": [],
        "status": "Running",
    }


@app.get("/health")
def health():
    return {"status": "ok", "project": "GoldenAPI"}


@app.get("/routes")
def routes():
    return {"routes": ['GET /', 'GET /health', 'GET /routes', 'POST /login', 'GET /users']}
