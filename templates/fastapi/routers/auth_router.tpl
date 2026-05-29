from fastapi import APIRouter, HTTPException

from services.token_service import TokenService
from services.validator import Validator

router = APIRouter()
tokens = TokenService()
validator = Validator()


@router.post("/login")
def login(payload: dict):
    errors = validator.validate(payload, {
        "email": ["required", "email"],
        "password": ["required", "min:6"],
    })

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    return {
        "token": tokens.generate({
            "email": payload["email"],
            "project": "{{project_name}}",
        }),
        "project": "{{project_name}}",
    }


@router.get("/users")
def get_users():
    return {"data": []}
