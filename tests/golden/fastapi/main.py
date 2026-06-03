from fastapi import FastAPI

from middleware.token_validation_middleware import TokenValidationMiddleware
from routers.auth import router as auth_router
from config.settings import settings

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(TokenValidationMiddleware)
app.include_router(auth_router)
