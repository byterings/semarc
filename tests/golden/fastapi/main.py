from fastapi import FastAPI

from middleware.token_validation_middleware import TokenValidationMiddleware
from config.settings import settings
from routers.auth import router as auth_router
from routers.user import router as user_router

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(TokenValidationMiddleware)
app.include_router(auth_router)
app.include_router(user_router)
