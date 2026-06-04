from fastapi import FastAPI

from middleware.token_validation_middleware import TokenValidationMiddleware
from config.settings import settings
{{router_imports}}

app = FastAPI(title=settings.APP_NAME)
app.add_middleware(TokenValidationMiddleware)
{{router_includes}}
