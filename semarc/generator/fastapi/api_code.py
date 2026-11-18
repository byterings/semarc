"""Renders FastAPI routers and the application entry point from IR routes."""
from semarc.compiler.version import SEMARC_VERSION
from semarc.generator.fastapi.entity_code import module_name
from semarc.generator.utils.inflector import snake_case
from semarc.generator.utils.resource_views import all_route_labels, field_rules, model_by_name, roles_feature, routes_for_model

DECORATORS = {"GET": "get", "POST": "post", "PUT": "put", "PATCH": "patch", "DELETE": "delete"}


def model_router_code(ir: dict, model: dict) -> str | None:
    routes = [route for route in routes_for_model(ir, model["name"]) if route["operation"]["kind"] != "custom"]
    if not routes:
        return None

    name = model["name"]
    module = module_name(name)
    roles = roles_feature(ir)
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
        auth_names = []
        if any(route["access"] == "protected" and not route.get("roles") for route in routes):
            auth_names.append("current_user_id")
        if any(route.get("roles") for route in routes):
            auth_names.append("require_roles")
        if roles and any(route["operation"].get("owner_only") for route in routes):
            auth_names.append("is_admin")
        lines.append(f"from middleware.auth import {', '.join(auth_names)}")
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
        lines.extend(_route_function(route, name, module, used_names, roles))
    lines.append("")
    return "\n".join(lines)


def _route_function(route: dict, name: str, module: str, used_names: set[str], roles: dict | None) -> list[str]:
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
    manage = ""
    if route["access"] == "protected":
        if route.get("roles"):
            allowed = ", ".join(repr(role) for role in route["roles"])
            arguments.append(f"current_user: int = Depends(require_roles({allowed}))")
        else:
            arguments.append("current_user: int = Depends(current_user_id)")
        owner = "current_user"
        if roles and operation.get("owner_only"):
            arguments.append("manage_all: bool = Depends(is_admin)")
            manage = ", manage_all=manage_all"
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
        "replace": f"    return {{\"data\": service.update({parameter}, payload, partial=False, owner_id={owner}{manage})}}",
        "update": f"    return {{\"data\": service.update({parameter}, payload, partial=True, owner_id={owner}{manage})}}",
        "delete": f"    service.delete({parameter}, {owner}{manage})\n    return Response(status_code=204)",
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
        auth_names = []
        if any(route["access"] == "protected" and not route.get("roles") for route in routes):
            auth_names.append("current_user_id")
        if any(route.get("roles") for route in routes):
            auth_names.append("require_roles")
        lines.append(f"from middleware.auth import {', '.join(auth_names)}")
    lines.extend(["", 'router = APIRouter(tags=["Custom"])'])

    used_names: set[str] = set()
    for route in routes:
        segments = [segment.strip("{}").replace("-", "_") for segment in route["path"].strip("/").split("/") if segment]
        function = _unique(f"{route['method'].lower()}_{'_'.join(segments) or 'root'}", used_names)
        arguments = [f"{parameter}: str" for parameter in route["parameters"]]
        if route.get("roles"):
            allowed = ", ".join(repr(role) for role in route["roles"])
            arguments.append(f"current_user: int = Depends(require_roles({allowed}))")
        elif route["access"] == "protected":
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
    secret_rules = field_rules(next(item for item in model["fields"] if item["name"] == secret))
    new_password = [f"min_length={secret_rules['min'] or 1}"]
    if secret_rules["max"]:
        new_password.append(f"max_length={secret_rules['max']}")
    return "\n".join(
        [
            "from fastapi import APIRouter, Depends, Response",
            "from pydantic import BaseModel, Field",
            "from sqlalchemy.orm import Session",
            "",
            *(["from typing import Literal", ""] if auth["features"]["roles"] else []),
            "from core.errors import ApiError",
            "from core.rate_limit import auth_rate_limit",
            "from core.refresh_tokens import RefreshTokenStore",
            *_mail_imports(auth),
            *_oauth_imports(auth),
            "from database import get_db",
            "from middleware.auth import current_user_id" + (", require_roles" if auth["features"]["roles"] else ""),
            *(["from config.settings import settings"] if auth["features"]["roles"] else []),
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
            "    refresh_token: str",
            "    refresh_expires_in: int",
            "",
            "",
            "class RefreshRequest(InputSchema):",
            "    refresh_token: str = Field(min_length=1)",
            "",
            "",
            "class PasswordChange(InputSchema):",
            "    current_password: str = Field(min_length=1)",
            f"    new_password: str = Field({', '.join(new_password)})",
            "",
            "",
            "def issue_session(db: Session, user_id: int) -> dict:",
            '    """Access token plus a new refresh token."""',
            "    return {**TokenService().issue(user_id), **RefreshTokenStore(db).issue(user_id)}",
            "",
            "",
            "class RegisterResult(TokenResult):",
            f"    user: {name}Read",
            "",
            "",
            '@router.post(',
            '    "/register",',
            "    status_code=201,",
            "    response_model=DataResponse[RegisterResult],",
            "    dependencies=[Depends(auth_rate_limit)],",
            ")",
            f"def register(payload: {name}Create, db: Session = Depends(get_db)) -> dict:",
            f"    user = {name}Service(db).create(payload)",
            *_bootstrap_admin_lines(auth, name),
            *(["    send_verification(db, user)"] if auth["features"]["email_verification"] else []),
            '    result = {"user": user, **issue_session(db, user["id"])}',
            '    return {"data": result}',
            "",
            "",
            '@router.post("/login", response_model=DataResponse[TokenResult], dependencies=[Depends(auth_rate_limit)])',
            "def login(payload: LoginRequest, db: Session = Depends(get_db)) -> dict:",
            f'    record = {name}Repository(db).find_by("{identity}", payload.{identity})',
            f"    if record is None or not PasswordHasher().verify(payload.{secret}, record.{secret}):",
            '        raise ApiError.unauthorized("Invalid credentials.")',
            '    return {"data": issue_session(db, record.id)}',
            "",
            "",
            '@router.post("/token/refresh", response_model=DataResponse[TokenResult], dependencies=[Depends(auth_rate_limit)])',
            "def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> dict:",
            "    user_id = RefreshTokenStore(db).rotate(payload.refresh_token)",
            f"    if {name}Repository(db).get(user_id) is None:",
            '        raise ApiError.unauthorized("Token user no longer exists.")',
            '    return {"data": issue_session(db, user_id)}',
            "",
            "",
            '@router.post("/logout", status_code=204)',
            "def logout(payload: RefreshRequest, db: Session = Depends(get_db)) -> Response:",
            "    RefreshTokenStore(db).revoke(payload.refresh_token)",
            "    return Response(status_code=204)",
            "",
            "",
            '@router.post("/me/password", status_code=204)',
            "def change_password(payload: PasswordChange, user_id: int = Depends(current_user_id), db: Session = Depends(get_db)) -> Response:",
            f"    repository = {name}Repository(db)",
            "    record = repository.get(user_id)",
            f"    if record is None or not PasswordHasher().verify(payload.current_password, record.{secret}):",
            '        raise ApiError.validation({"current_password": ["current_password is incorrect"]})',
            f'    repository.update(record, {{"{secret}": PasswordHasher().hash(payload.new_password)}})',
            "    RefreshTokenStore(db).revoke_all(user_id)",
            "    return Response(status_code=204)",
            *_mail_route_lines(auth, name, new_password),
            "",
            "",
            f'@router.get("/me", response_model=DataResponse[{name}Read])',
            "def me(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)) -> dict:",
            f'    return {{"data": {name}Service(db).get(user_id)}}',
            *_role_route_lines(auth, name),
            *_oauth_route_lines(auth, model),
            "",
        ]
    )


def _oauth_imports(auth: dict) -> list[str]:
    if not auth["features"]["oauth"]:
        return []
    lines = ["from secrets import token_hex", "from sqlalchemy import select", "from core import oauth", "from core.oauth import OAuthAccount"]
    if auth["features"]["email_verification"]:
        lines.append("from database import utc_now")
    return lines


def _oauth_route_lines(auth: dict, model: dict) -> list[str]:
    oauth = auth["features"]["oauth"]
    if not oauth:
        return []
    name = model["name"]
    identity, secret = auth["identity_field"], auth["secret_field"]
    roles = auth["features"]["roles"]
    verification = auth["features"]["email_verification"]
    new_user = [
        "            data = {",
        f'                "{identity}": identity["{identity}"],',
        f'                "{secret}": PasswordHasher().hash(token_hex(32)),',
        "            }",
    ]
    name_field = oauth["name_field"]
    if name_field:
        limit = field_rules(next(item for item in model["fields"] if item["name"] == name_field))["max"] or 255
        new_user.append(f'            data["{name_field}"] = identity["name"][:{limit}]')
    if roles:
        new_user += [
            f'            admin = settings.bootstrap_admin_email and identity["{identity}"].lower() == settings.bootstrap_admin_email.lower()',
            f'            data["role"] = {roles["admin"]!r} if admin else {roles["default"]!r}',
        ]
    if verification:
        new_user.append(f'            data["{verification["field"]}"] = utc_now()')
    if verification:
        relink = [
            f"        elif record.{verification['field']} is None:",
            "            # Ownership of the address is proven by the provider, not by whoever set the password.",
            f'            repository.update(record, {{"{secret}": PasswordHasher().hash(token_hex(32)), "{verification["field"]}": utc_now()}})',
            "            RefreshTokenStore(db).revoke_all(record.id)",
        ]
    else:
        relink = [
            "        else:",
            "            # Ownership of the address is proven by the provider, not by whoever set the password.",
            f'            repository.update(record, {{"{secret}": PasswordHasher().hash(token_hex(32))}})',
            "            RefreshTokenStore(db).revoke_all(record.id)",
        ]
    lines = [
        "",
        "",
        "class OAuthStart(BaseModel):",
        "    authorization_url: str",
        "    state: str",
        "",
        "",
        "class OAuthCallback(InputSchema):",
        "    code: str = Field(min_length=1)",
        "    state: str = Field(min_length=1)",
        "",
        "",
        "def oauth_sign_in(db: Session, provider: str, payload: OAuthCallback) -> dict:",
        '    """Finds the user linked to the provider identity, links one by verified email, or creates one."""',
        "    oauth.verify_state(provider, payload.state)",
        "    profile = oauth.fetch_identity(provider, payload.code)",
        f'    identity = {{"{identity}": profile["email"], "name": profile["name"]}}',
        '    account = db.scalars(select(OAuthAccount).filter_by(provider_subject=profile["subject"])).first()',
        "    if account is not None:",
        "        user_id = account.user_id",
        "    else:",
        f"        repository = {name}Repository(db)",
        f'        record = repository.find_by("{identity}", identity["{identity}"])',
        "        if record is None:",
        *new_user,
        "            record = repository.create(data)",
        *relink,
        '        db.add(OAuthAccount(provider=provider, provider_subject=profile["subject"], user_id=record.id))',
        "        db.commit()",
        "        user_id = record.id",
        f'    result = {{"user": {name}Service(db).get(user_id), **issue_session(db, user_id)}}',
        '    return {"data": result}',
    ]
    for provider in oauth["providers"]:
        key = provider["name"]
        lines += [
            "",
            "",
            f'@router.get("/oauth/{key}", response_model=DataResponse[OAuthStart])',
            f"def oauth_start_{key}() -> dict:",
            f'    return {{"data": oauth.start("{key}")}}',
            "",
            "",
            f'@router.post("/oauth/{key}/callback", response_model=DataResponse[RegisterResult], dependencies=[Depends(auth_rate_limit)])',
            f"def oauth_callback_{key}(payload: OAuthCallback, db: Session = Depends(get_db)) -> dict:",
            f'    return oauth_sign_in(db, "{key}", payload)',
        ]
    return lines


def _mail_imports(auth: dict) -> list[str]:
    features = auth["features"]
    if not (features["password_reset"] or features["email_verification"]):
        return []
    models = [cls for feature, cls in [("password_reset", "PasswordReset"), ("email_verification", "EmailVerification")] if features[feature]]
    lines = ["from core.mailer import mail_body, send_mail", f"from core.one_time_tokens import {', '.join(models)}, OneTimeTokens"]
    if features["email_verification"]:
        lines.append("from database import utc_now")
    return lines


def _mail_route_lines(auth: dict, name: str, new_password: list[str]) -> list[str]:
    identity, secret = auth["identity_field"], auth["secret_field"]
    lines: list[str] = []
    reset = auth["features"]["password_reset"]
    if reset:
        lines += [
            "",
            "",
            "class ForgotPassword(InputSchema):",
            f"    {identity}: str = Field(min_length=1)",
            "",
            "",
            "class ResetPassword(InputSchema):",
            "    token: str = Field(min_length=1)",
            f"    {secret}: str = Field({', '.join(new_password)})",
            "",
            "",
            '@router.post("/password/forgot", status_code=202, dependencies=[Depends(auth_rate_limit)])',
            "def forgot_password(payload: ForgotPassword, db: Session = Depends(get_db)) -> dict:",
            f'    record = {name}Repository(db).find_by("{identity}", payload.{identity})',
            "    if record is not None:",
            f"        token = OneTimeTokens(db, PasswordReset).issue(record.id, {reset['ttl_seconds']})",
            "        body = mail_body(",
            '            "Use this token to reset your password.",',
            "            token,",
            '            "reset-password",',
            f'            "The token expires in {reset["ttl_seconds"] // 60} minutes. If you did not ask for a reset, ignore this email.",',
            "        )",
            f'        send_mail(payload.{identity}, "Reset your password", body)',
            '    message = "If the account exists, a reset email has been sent."',
            '    return {"data": dict(message=message)}',
            "",
            "",
            '@router.post("/password/reset", status_code=204)',
            "def reset_password(payload: ResetPassword, db: Session = Depends(get_db)) -> Response:",
            "    user_id = OneTimeTokens(db, PasswordReset).consume(payload.token)",
            "    if user_id is None:",
            '        raise ApiError.validation({"token": ["token is invalid or expired"]})',
            f"    repository = {name}Repository(db)",
            f'    repository.update(repository.get(user_id), {{"{secret}": PasswordHasher().hash(payload.{secret})}})',
            "    RefreshTokenStore(db).revoke_all(user_id)",
            "    return Response(status_code=204)",
        ]
    verification = auth["features"]["email_verification"]
    if verification:
        field = verification["field"]
        lines += [
            "",
            "",
            "class VerifyEmail(InputSchema):",
            "    token: str = Field(min_length=1)",
            "",
            "",
            "def send_verification(db: Session, user: dict) -> None:",
            f"    token = OneTimeTokens(db, EmailVerification).issue(user[\"id\"], {verification['ttl_seconds']})",
            "    body = mail_body(",
            '        "Use this token to confirm your email address.",',
            "        token,",
            '        "verify-email",',
            f'        "The token expires in {verification["ttl_seconds"] // 3600} hours.",',
            "    )",
            f'    send_mail(user["{identity}"], "Verify your email address", body)',
            "",
            "",
            f'@router.post("/email/verify", response_model=DataResponse[{name}Read])',
            "def verify_email(payload: VerifyEmail, db: Session = Depends(get_db)) -> dict:",
            "    user_id = OneTimeTokens(db, EmailVerification).consume(payload.token)",
            "    if user_id is None:",
            '        raise ApiError.validation({"token": ["token is invalid or expired"]})',
            f"    repository = {name}Repository(db)",
            f'    repository.update(repository.get(user_id), {{"{field}": utc_now()}})',
            f'    return {{"data": {name}Service(db).get(user_id)}}',
            "",
            "",
            '@router.post("/email/resend", status_code=202)',
            "def resend_verification(user_id: int = Depends(current_user_id), db: Session = Depends(get_db)) -> dict:",
            f"    user = {name}Service(db).get(user_id)",
            f'    if user["{field}"] is None:',
            "        send_verification(db, user)",
            '    message = "A verification email is sent when the address is not verified yet."',
            '    return {"data": dict(message=message)}',
        ]
    return lines


def _bootstrap_admin_lines(auth: dict, name: str) -> list[str]:
    roles = auth["features"]["roles"]
    if not roles:
        return []
    identity = auth["identity_field"]
    return [
        f'    if settings.bootstrap_admin_email and user["{identity}"].lower() == settings.bootstrap_admin_email.lower():',
        f"        record = {name}Repository(db).get(user[\"id\"])",
        f"        {name}Repository(db).update(record, {{\"role\": {roles['admin']!r}}})",
        f'        user = {name}Service(db).get(user["id"])',
    ]


def _role_route_lines(auth: dict, name: str) -> list[str]:
    roles = auth["features"]["roles"]
    if not roles:
        return []
    choices = ", ".join(repr(role) for role in roles["names"])
    return [
        "",
        "",
        "class RoleChange(InputSchema):",
        f"    role: Literal[{choices}]",
        "",
        "",
        f'@router.put("/users/{{id}}/role", response_model=DataResponse[{name}Read])',
        "def set_role(",
        "    id: int,",
        "    payload: RoleChange,",
        f"    admin_id: int = Depends(require_roles({roles['admin']!r})),",
        "    db: Session = Depends(get_db),",
        ") -> dict:",
        f"    record = {name}Repository(db).get(id)",
        "    if record is None:",
        f'        raise ApiError.not_found(f"{name} {{id}} not found.")',
        f'    {name}Repository(db).update(record, {{"role": payload.role}})',
        f'    return {{"data": {name}Service(db).get(id)}}',
    ]


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
            "import json",
            "from html import escape",
            "from pathlib import Path",
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
            'OPENAPI_DOCUMENT = json.loads((Path(__file__).resolve().parent / "openapi.json").read_text(encoding="utf-8"))',
            "",
            'app = FastAPI(title=PROJECT["project"], version="0.1.0")',
            "app.openapi = lambda: OPENAPI_DOCUMENT  # the SEMARC contract, shared by every target",
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
