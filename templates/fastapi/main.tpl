from fastapi import FastAPI

from middleware.token_validation_middleware import TokenValidationMiddleware
from config.settings import settings
{{router_imports}}

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(TokenValidationMiddleware)
{{router_includes}}


@app.get("/")
def home():
    return {
        "title": "SEMARC Generated Project",
        "project": "{{project_name}}",
        "target": "FastAPI",
        "semarc_version": "{{semarc_version}}",
        "models": {{models}},
        "routes": {{routes}},
        "profiles": {{profiles}},
        "modules": {{modules}},
        "status": "Running",
    }


@app.get("/health")
def health():
    return {"status": "ok", "project": "{{project_name}}"}


@app.get("/routes")
def routes():
    return {"routes": {{routes}}}
