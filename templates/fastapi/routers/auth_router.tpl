from fastapi import APIRouter, HTTPException

from services.validator import Validator

router = APIRouter()
validator = Validator()


@router.post("/login")
def login(payload: dict):
    errors = validator.validate(payload, {
        "email": ["required", "email"],
        "password": ["required", "min:6"],
    })

    if errors:
        raise HTTPException(status_code=422, detail=errors)

    raise HTTPException(
        status_code=501,
        detail="Authentication implementation is a generated TODO scaffold.",
    )


@router.get("/users")
def get_users():
    raise HTTPException(
        status_code=501,
        detail="Connect this route to a generated business service.",
    )
