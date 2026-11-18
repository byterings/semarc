"""Renders FastAPI routers and the application entry point from IR routes."""
from compiler.version import SEMARC_VERSION
from generator.fastapi.entity_code import module_name
from generator.utils.inflector import snake_case
from generator.utils.resource_views import all_route_labels, model_by_name, routes_for_model

DECORATORS = {"GET": "get", "POST": "post", "PUT": "put", "PATCH": "patch", "DELETE": "delete"}


def model_router_code(ir: dict, model: dict) -> str | None:
    routes = [route for route in routes_for_model(ir, model["name"]) if route["operation"]["kind"] != "custom"]
    if not routes:
        return None

    name = model["name"]
    module = module_name(name)
    protected = any(route["access"] == "protected" for route in routes)
    parents = sorted({route["operation"]["parent_model"] for route in routes if route["operation"]["kind"] == "list_related"})
    kinds = {route["operation"]["kind"] for route in routes}

    fastapi_names = ["APIRouter", "Depends"]
    if kinds & {"list", "list_related"}:
        fastapi_names.append("Request")
    if "delete" in kinds:
        fastapi_names.append("Response")
    lines = [f"from fastapi import {', '.join(fastapi_names)}"]
    lines.extend(["from sqlalchemy.orm import Session", "", "from database import get_db"])
    if protected:
        lines.append("from middleware.auth import current_user_id")
    lines.extend(f"from models.{module_name(parent)} import {parent}" for parent in parents)
    schemas = [f"{name}Read"]
    if kinds & {"create", "replace"}:
        schemas.insert(0, f"{name}Create")
    if "update" in kinds:
        schemas.append(f"{name}Update")
    lines.extend(
        [
            "from schemas.base import "
            + ", ".join(
                name
                for name, used in [
                    ("DataResponse", bool(kinds - {"list", "list_related", "delete"})),
                    ("ListResponse", bool(kinds & {"list", "list_related"})),
                ]
                if used
            ),
            f"from schemas.{module} import {', '.join(schemas)}",
            "from services.base import DEFAULT_LIMIT",
            f"from services.{module}_service import {name}Service",
            "",
            f'router = APIRouter(tags=["{name}"])',
            "",
            "",
            f"def get_service(db: Session = Depends(get_db)) -> {name}Service:",
            f"    return {name}Service(db)",
        ]
    )

    used_names: set[str] = set()
    for route in routes:
        lines.extend(["", ""])
        lines.extend(_route_function(route, name, module, used_names))
    lines.append("")
    return "\n".join(lines)


def _route_function(route: dict, name: str, module: str, used_names: set[str]) -> list[str]:
    operation = route["operation"]
    kind = operation["kind"]
    collection = snake_case(route["path"].strip("/").split("/")[-1].replace("-", "_")) or module
    if kind == "list_related":
        function = f"list_{collection}_by_{module_name(operation['parent_model'])}"
    elif kind == "list":
        function = f"list_{collection}"
    else:
        function = f"{kind}_{module}"
    function = _unique(function, used_names)

    parameter = operation.get("parameter")
    arguments = []
    if parameter:
        arguments.append(f"{parameter}: int")
    if kind in {"create", "replace"}:
        arguments.append(f"payload: {name}Create")
    if kind == "update":
        arguments.append(f"payload: {name}Update")
    if kind in {"list", "list_related"}:
        arguments.extend(["http_request: Request", "limit: int = DEFAULT_LIMIT", "offset: int = 0"])
    owner = "None"
    if route["access"] == "protected":
        arguments.append("current_user: int = Depends(current_user_id)")
        owner = "current_user"
    arguments.append(f"service: {name}Service = Depends(get_service)")

    decorator_options = [f'"{route["path"]}"']
    if kind in {"list", "list_related"}:
        decorator_options.append(f"response_model=ListResponse[{name}Read]")
    elif kind == "delete":
        decorator_options.append("status_code=204")
    else:
        decorator_options.append(f"response_model=DataResponse[{name}Read]")
    if kind == "create":
        decorator_options.append("status_code=201")

    body = {
        "list": "    return service.list(limit, offset, http_request.query_params)",
        "read": f"    return {{\"data\": service.get({parameter})}}",
        "create": f"    return {{\"data\": service.create(payload, {owner})}}",
        "replace": f"    return {{\"data\": service.update({parameter}, payload, partial=False, owner_id={owner})}}",
        "update": f"    return {{\"data\": service.update({parameter}, payload, partial=True, owner_id={owner})}}",
        "delete": f"    service.delete({parameter}, {owner})\n    return Response(status_code=204)",
        "list_related": (
            f"    return service.list_for_parent({operation.get('parent_model')}, \"{operation.get('parent_model')}\", "
            f"\"{operation.get('foreign_key')}\", {parameter}, limit, offset, http_request.query_params)"
        ),
    }[kind]
    return_type = "Response" if kind == "delete" else "dict"
    return [
        f"@router.{DECORATORS[route['method']]}({', '.join(decorator_options)})",
        f"def {function}({', '.join(arguments)}) -> {return_type}:",
        body,
    ]


def _unique(function: str, used_names: set[str]) -> str:
    candidate, index = function, 2
    while candidate in used_names:
        candidate = f"{function}_{index}"
        index += 1
    used_names.add(candidate)
    return candidate


def custom_router_code(ir: dict) -> str | None:
    routes = [route for route in ir["routes"] if route["operation"]["kind"] == "custom"]
    if not routes:
        return None
    protected = any(route["access"] == "protected" for route in routes)
    lines = ["from fastapi import APIRouter"]
    if protected:
        lines[0] = "from fastapi import APIRouter, Depends"
    lines.extend(["", "from core.errors import ApiError"])
    if protected:
        lines.append("from middleware.auth import current_user_id")
    lines.extend(["", 'router = APIRouter(tags=["Custom"])'])

    used_names: set[str] = set()
    for route in routes:
        segments = [segment.strip("{}").replace("-", "_") for segment in route["path"].strip("/").split("/") if segment]
        function = _unique(f"{route['method'].lower()}_{'_'.join(segments) or 'root'}", used_names)
        arguments = [f"{parameter}: str" for parameter in route["parameters"]]
        if route["access"] == "protected":
            arguments.append("current_user: int = Depends(current_user_id)")
        message = (
            f"{route['method']} {route['path']} is declared in the semantic source but has no generated behaviour. "
            f"Implement it in routers/custom.py."
        )
        lines.extend(
            [
                "",
                "",
                f'@router.{DECORATORS[route["method"]]}("{route["path"]}")',
                f"def {function}({', '.join(arguments)}) -> dict:",
                f"    raise ApiError.not_implemented({message!r})",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def auth_router_code(ir: dict) -> str:
    auth = ir["auth"]
    model = model_by_name(ir, auth["model"])
    name = model["name"]
    module = module_name(name)
    identity, secret = auth["identity_field"], auth["secret_field"]
    return "\n".join(
        [
            "from fastapi import APIRouter, Depends",
            "from pydantic import BaseModel, Field",
            "from sqlalchemy.orm import Session",
            "",
            "from core.errors import ApiError",
            "from database import get_db",
            "from middleware.auth import current_user_id",
            f"from repositories.{module}_repository import {name}Repository",
            "from schemas.base import DataResponse, InputSchema",
            f"from schemas.{module} import {name}Create, {name}Read",
            "from services.password_hasher import PasswordHasher",
            "from services.token_service import TokenService",
            f"from services.{module}_service import {name}Service",
            "",
            'router = APIRouter(tags=["Auth"])',
            "",
            "",
            "class LoginRequest(InputSchema):",
            f"    {identity}: str = Field(min_length=1)",
            f"    {secret}: str = Field(min_length=1)",
            "",
            "",
            "class TokenResult(BaseModel):",
            "    access_token: str",
            "    token_type: str",
            "    expires_in: int",
            "",
            "",
            "class RegisterResult(TokenResult):",
            f"    user: {name}Read",
            "",
            "",
            '@router.post("/register", status_code=201, response_model=DataResponse[RegisterResult])',
            f"def register(payload: {name}Create, db: Session = Depends(get_db)) -> dict:",
            f"    user = {name}Service(db).create(payload)",
            '    result = {"user": user, **TokenService().issue(user["id"])}',
            '    return {"data": result}',
            "",
            "",
            '@router.post("/login", response_model=DataResponse[TokenResult])',
            "def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:",
            f'    record = {name}Repository(db).find_by("{identity}", payload.{identity})',
            f"    if record is None or not PasswordHasher().verify(payload.{secret}, record.{secret}):",
            '        raise ApiError.unauthorized("Invalid credentials.")',
            '    return {"data": TokenService().issue(record.id)}',
            "",
            "",
            f'@router.get("/me", response_model=DataResponse[{name}Read])',
            "def me(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)) -> dict:",
            f'    return {{"data": {name}Service(db).get(user_id)}}',
            "",
        ]
    )


def main_code(ir: dict, routers: list[str]) -> str:
    project = {
        "project": ir["project"],
        "target": "FASTAPI",
        "semarc_version": SEMARC_VERSION,
        "models": [model["name"] for model in ir["models"]],
        "routes": all_route_labels(ir),
    }
    imports = [f"from routers.{router} import router as {router}_router" for router in routers]
    includes = [f"app.include_router({router}_router)" for router in routers]
    return "\n".join(
        [
            "from html import escape",
            "",
            "from fastapi import FastAPI",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from fastapi.responses import HTMLResponse, JSONResponse",
            "from sqlalchemy import text",
            "",
            "from config.settings import settings",
            "from core.errors import register_error_handlers",
            "from database import engine",
            *imports,
            "",
            "PROJECT = {",
            f'    "project": {project["project"]!r},',
            f'    "target": {project["target"]!r},',
            f'    "semarc_version": {project["semarc_version"]!r},',
            f'    "models": {project["models"]!r},',
            f'    "routes": {project["routes"]!r},',
            "}",
            "",
            'app = FastAPI(title=PROJECT["project"], version="0.1.0")',
            "register_error_handlers(app)",
            "app.add_middleware(",
            "    CORSMiddleware,",
            "    allow_origins=settings.cors_origins,",
            '    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],',
            '    allow_headers=["Authorization", "Content-Type"],',
            "    max_age=600,",
            ")",
            "",
            "",
            '@app.get("/", response_class=HTMLResponse, include_in_schema=False)',
            "def home() -> str:",
            '    models = "".join(f"<li>{escape(model)}</li>" for model in PROJECT["models"])',
            '    routes = "".join(f"<li>{escape(route)}</li>" for route in PROJECT["routes"])',
            "    return (",
            '        f"<!doctype html><html><head><meta charset=\\"utf-8\\"><title>{escape(PROJECT[\'project\'])}</title></head><body>"',
            '        "<h1>SEMARC Generated Project</h1>"',
            '        f"<p><strong>Project:</strong> {escape(PROJECT[\'project\'])}</p>"',
            '        f"<p><strong>Target:</strong> {PROJECT[\'target\']}</p>"',
            '        f"<p><strong>SEMARC Version:</strong> {PROJECT[\'semarc_version\']}</p>"',
            '        f"<h2>Models</h2><ul>{models}</ul><h2>Routes</h2><ul>{routes}</ul>"',
            '        "<p><strong>Status:</strong> Running</p></body></html>"',
            "    )",
            "",
            "",
            '@app.get("/health")',
            "def health() -> JSONResponse:",
            "    try:",
            "        with engine.connect() as connection:",
            '            connection.execute(text("SELECT 1"))',
            '        database = "ok"',
            "    except Exception:",
            '        database = "unavailable"',
            '    status = "ok" if database == "ok" else "degraded"',
            "    return JSONResponse(",
            '        {"status": status, "project": PROJECT["project"], "database": database},',
            '        status_code=200 if database == "ok" else 503,',
            "    )",
            "",
            "",
            '@app.get("/routes")',
            "def routes() -> dict:",
            '    return {"routes": PROJECT["routes"]}',
            "",
            "",
            *includes,
            "",
        ]
    )
