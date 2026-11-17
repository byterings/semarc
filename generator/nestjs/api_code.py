"""Renders NestJS controllers, auth module, app module and TypeORM wiring from IR."""
from compiler.version import SEMARC_VERSION
from generator.nestjs.typescript import Imports, file_base, folder, route_path, service_property, ts_string
from generator.utils.inflector import pascal_case
from generator.utils.resource_views import all_route_labels, model_by_name, routes_for_model

HTTP_DECORATORS = {"GET": "Get", "POST": "Post", "PUT": "Put", "PATCH": "Patch", "DELETE": "Delete"}
MIGRATION_EPOCH = 1700000000000


def controller_code(ir: dict, model: dict, reserved: set[str]) -> str | None:
    routes = [route for route in routes_for_model(ir, model["name"]) if route["operation"]["kind"] != "custom"]
    if not routes:
        return None
    name = model["name"]
    service = service_property(name)
    imports = Imports(reserved)
    controller = imports.use("@nestjs/common", "Controller")
    imports.use(f"./{folder(name)}.service", f"{name}Service")

    methods = []
    used: set[str] = set()
    for route in routes:
        methods.append(_controller_method(ir, route, name, service, imports, used))

    lines = [f"@{controller}()", f"export class {name}Controller {{", f"  constructor(private readonly {service}: {name}Service) {{}}", ""]
    lines.append("\n\n".join(methods))
    lines.extend(["}", ""])
    return "\n".join(imports.render() + [""] + lines)


def _controller_method(ir: dict, route: dict, name: str, service: str, imports: Imports, used: set[str]) -> str:
    operation = route["operation"]
    kind = operation["kind"]
    decorator = imports.use("@nestjs/common", HTTP_DECORATORS[route["method"]])
    decorators = [f"  @{decorator}({ts_string(route_path(route['path']))})"]
    if kind == "create":
        decorators.append(f"  @{imports.use('@nestjs/common', 'HttpCode')}(201)")
    if kind == "delete":
        decorators.append(f"  @{imports.use('@nestjs/common', 'HttpCode')}(204)")
    protected = route["access"] == "protected"
    if protected:
        decorators.append(f"  @{imports.use('@nestjs/common', 'UseGuards')}(AuthGuard)")
        imports.use("../../guards/auth.guard", "AuthGuard")

    parameters = []
    parameter = operation.get("parameter")
    if parameter:
        param = imports.use("@nestjs/common", "Param")
        imports.use("../../common/id.pipe", "IdPipe")
        parameters.append(f"@{param}({ts_string(parameter)}, IdPipe) id: number")
    if kind in {"create", "replace"}:
        imports.use(f"./dto/create-{file_base(name)}.dto", f"Create{name}Dto")
        parameters.append(f"@{imports.use('@nestjs/common', 'Body')}() dto: Create{name}Dto")
    if kind == "update":
        imports.use(f"./dto/update-{file_base(name)}.dto", f"Update{name}Dto")
        parameters.append(f"@{imports.use('@nestjs/common', 'Body')}() dto: Update{name}Dto")
    if kind in {"list", "list_related"}:
        query = imports.use("@nestjs/common", "Query")
        imports.use("../../common/resource.service", "pageParams")
        parameters.extend([f"@{query}('limit') limit?: string", f"@{query}('offset') offset?: string"])
    owner = "undefined"
    if protected and kind in {"create", "replace", "update", "delete"}:
        imports.use("../../common/current-user.decorator", "CurrentUserId")
        parameters.append("@CurrentUserId() userId?: number")
        owner = "userId"

    if kind == "list_related":
        method = f"listBy{pascal_case(operation['parent_model'])}"
    else:
        method = {"list": "list", "read": "read", "create": "create", "replace": "replace", "update": "update", "delete": "remove"}[kind]
    method = _unique(method, used)

    body = {
        "list": f"    return this.{service}.list(...pageParams(limit, offset));",
        "read": f"    return {{ data: await this.{service}.get(id) }};",
        "create": f"    return {{ data: await this.{service}.create(dto, {owner}) }};",
        "replace": f"    return {{ data: await this.{service}.update(id, dto, false, {owner}) }};",
        "update": f"    return {{ data: await this.{service}.update(id, dto, true, {owner}) }};",
        "delete": f"    await this.{service}.delete(id, {owner});",
        "list_related": (
            f"    return this.{service}.listForParent("
            f"{ts_string(model_by_name(ir, operation['parent_model'])['table']) if kind == 'list_related' else ''}, "
            f"{ts_string(operation.get('parent_model', ''))}, {ts_string(operation.get('foreign_key', ''))}, "
            "id, ...pageParams(limit, offset));"
        ),
    }[kind]
    asynchronous = "" if kind == "list" else "async "
    return "\n".join(decorators + [f"  {asynchronous}{method}({', '.join(parameters)}) {{", body, "  }"])


def _unique(name: str, used: set[str]) -> str:
    candidate, index = name, 2
    while candidate in used:
        candidate = f"{name}{index}"
        index += 1
    used.add(candidate)
    return candidate


def custom_code(ir: dict, reserved: set[str]) -> tuple[str, str] | None:
    routes = [route for route in ir["routes"] if route["operation"]["kind"] == "custom"]
    if not routes:
        return None
    imports = Imports(reserved)
    controller = imports.use("@nestjs/common", "Controller")
    imports.use("../../common/api-error", "ApiError")
    methods = []
    used: set[str] = set()
    for route in routes:
        decorators = [f"  @{imports.use('@nestjs/common', HTTP_DECORATORS[route['method']])}({ts_string(route_path(route['path']))})"]
        if route["access"] == "protected":
            decorators.append(f"  @{imports.use('@nestjs/common', 'UseGuards')}(AuthGuard)")
            imports.use("../../guards/auth.guard", "AuthGuard")
        segments = [pascal_case(segment.strip("{}").replace("-", "_")) for segment in route["path"].strip("/").split("/") if segment]
        method = _unique(route["method"].lower() + "".join(segments), used)
        message = (
            f"{route['method']} {route['path']} is declared in the semantic source but has no generated behaviour. "
            "Implement it in src/modules/custom/custom.controller.ts."
        )
        methods.append("\n".join(decorators + [f"  {method}(): never {{", f"    throw ApiError.notImplemented({ts_string(message)});", "  }"]))

    controller_source = "\n".join(
        imports.render() + ["", f"@{controller}()", "export class CustomController {", "\n\n".join(methods), "}", ""]
    )
    module_imports = Imports(reserved)
    module = module_imports.use("@nestjs/common", "Module")
    module_imports.use("./custom.controller", "CustomController")
    module_source = "\n".join(
        module_imports.render() + ["", f"@{module}({{", "  controllers: [CustomController],", "})", "export class CustomModule {}", ""]
    )
    return controller_source, module_source


def auth_code(ir: dict, reserved: set[str]) -> dict[str, str]:
    auth = ir["auth"]
    name = model_by_name(ir, auth["model"])["name"]
    identity, secret = auth["identity_field"], auth["secret_field"]
    model_folder, model_file = folder(name), file_base(name)

    imports = Imports(reserved)
    controller = imports.use("@nestjs/common", "Controller")
    body = imports.use("@nestjs/common", "Body")
    get = imports.use("@nestjs/common", "Get")
    post = imports.use("@nestjs/common", "Post")
    http_code = imports.use("@nestjs/common", "HttpCode")
    use_guards = imports.use("@nestjs/common", "UseGuards")
    imports.use("../../common/api-error", "ApiError")
    imports.use("../../common/current-user.decorator", "CurrentUserId")
    imports.use("../../common/password-hasher", "PasswordHasher")
    imports.use("../../guards/auth.guard", "AuthGuard")
    imports.use(f"../{model_folder}/{model_folder}.repository", f"{name}Repository")
    imports.use(f"../{model_folder}/{model_folder}.service", f"{name}Service")
    imports.use(f"../{model_folder}/dto/create-{model_file}.dto", f"Create{name}Dto")
    imports.use("./dto/login.dto", "LoginDto")
    imports.use("./token.service", "TokenService")
    controller_source = "\n".join(
        imports.render()
        + [
            "",
            f"@{controller}()",
            "export class AuthController {",
            "  constructor(",
            f"    private readonly users: {name}Service,",
            f"    private readonly repository: {name}Repository,",
            "    private readonly tokens: TokenService,",
            "    private readonly hasher: PasswordHasher,",
            "  ) {}",
            "",
            f"  @{post}('register')",
            f"  @{http_code}(201)",
            f"  async register(@{body}() dto: Create{name}Dto) {{",
            "    const user = await this.users.create(dto);",
            "    const token = await this.tokens.issue(user.id as number);",
            "    return { data: { user, ...token } };",
            "  }",
            "",
            f"  @{post}('login')",
            f"  @{http_code}(200)",
            f"  async login(@{body}() dto: LoginDto) {{",
            f"    const record = await this.repository.findBy({ts_string(identity)}, dto.{identity});",
            f"    if (!record || !(await this.hasher.verify(dto.{secret}, record.{secret}))) {{",
            "      throw ApiError.unauthorized('Invalid credentials.');",
            "    }",
            "    return { data: await this.tokens.issue(record.id) };",
            "  }",
            "",
            f"  @{get}('me')",
            f"  @{use_guards}(AuthGuard)",
            "  async me(@CurrentUserId() userId: number) {",
            "    return { data: await this.users.get(userId) };",
            "  }",
            "}",
            "",
        ]
    )

    module_imports = Imports(reserved)
    global_ = module_imports.use("@nestjs/common", "Global")
    module = module_imports.use("@nestjs/common", "Module")
    module_imports.use("@nestjs/jwt", "JwtModule")
    module_imports.use("../../guards/auth.guard", "AuthGuard")
    module_imports.use(f"../{model_folder}/{model_folder}.module", f"{name}Module")
    module_imports.use("./auth.controller", "AuthController")
    module_imports.use("./token.service", "TokenService")
    module_source = "\n".join(
        module_imports.render()
        + [
            "",
            f"@{global_}()",
            f"@{module}({{",
            f"  imports: [JwtModule.register({{}}), {name}Module],",
            "  controllers: [AuthController],",
            "  providers: [TokenService, AuthGuard],",
            "  exports: [TokenService, AuthGuard],",
            "})",
            "export class AuthModule {}",
            "",
        ]
    )

    dto_imports = Imports(reserved)
    is_string = dto_imports.use("class-validator", "IsString")
    min_length = dto_imports.use("class-validator", "MinLength")
    dto_source = "\n".join(
        dto_imports.render()
        + [
            "",
            "export class LoginDto {",
            f"  @{is_string}()",
            f"  @{min_length}(1)",
            f"  {identity}!: string;",
            "",
            f"  @{is_string}()",
            f"  @{min_length}(1)",
            f"  {secret}!: string;",
            "}",
            "",
        ]
    )
    return {
        "src/modules/auth/auth.controller.ts": controller_source,
        "src/modules/auth/auth.module.ts": module_source,
        "src/modules/auth/dto/login.dto.ts": dto_source,
    }


def app_module_code(ir: dict, modules: list[tuple[str, str]], reserved: set[str]) -> str:
    imports = Imports(reserved)
    module = imports.use("@nestjs/common", "Module")
    typeorm = imports.use("@nestjs/typeorm", "TypeOrmModule")
    imports.use("./app.controller", "AppController")
    imports.use("./database/data-source", "dataSourceOptions")
    for class_name, path in modules:
        imports.use(path, class_name)
    return "\n".join(
        imports.render()
        + [
            "",
            f"@{module}({{",
            "  imports: [",
            f"    {typeorm}.forRoot({{ ...dataSourceOptions(), migrationsRun: true, retryAttempts: 30, retryDelay: 2000 }}),",
            *[f"    {class_name}," for class_name, _ in modules],
            "  ],",
            "  controllers: [AppController],",
            "})",
            "export class AppModule {}",
            "",
        ]
    )


def app_controller_code(ir: dict, reserved: set[str]) -> str:
    project = {
        "project": ir["project"],
        "target": "NESTJS",
        "semarc_version": SEMARC_VERSION,
        "models": [model["name"] for model in ir["models"]],
        "routes": all_route_labels(ir),
    }

    def array(values: list[str]) -> str:
        return "[" + ", ".join(ts_string(value) for value in values) + "]"

    return "\n".join(
        [
            "import { Controller, Get, Header, Res } from '@nestjs/common';",
            "import { Response } from 'express';",
            "import { DataSource } from 'typeorm';",
            "",
            "const PROJECT = {",
            f"  project: {ts_string(project['project'])},",
            f"  target: {ts_string(project['target'])},",
            f"  semarcVersion: {ts_string(project['semarc_version'])},",
            f"  models: {array(project['models'])},",
            f"  routes: {array(project['routes'])},",
            "};",
            "",
            "const escape = (value: string): string =>",
            "  value.replace(/[&<>\"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;', \"'\": '&#39;' })[char] as string);",
            "",
            "@Controller()",
            "export class AppController {",
            "  constructor(private readonly dataSource: DataSource) {}",
            "",
            "  @Get()",
            "  @Header('Content-Type', 'text/html; charset=utf-8')",
            "  home(): string {",
            "    const list = (items: string[]) => items.map((item) => `<li>${escape(item)}</li>`).join('');",
            "    return (",
            "      `<!doctype html><html><head><meta charset=\"utf-8\"><title>${escape(PROJECT.project)}</title></head><body>` +",
            "      '<h1>SEMARC Generated Project</h1>' +",
            "      `<p><strong>Project:</strong> ${escape(PROJECT.project)}</p>` +",
            "      `<p><strong>Target:</strong> ${PROJECT.target}</p>` +",
            "      `<p><strong>SEMARC Version:</strong> ${PROJECT.semarcVersion}</p>` +",
            "      `<h2>Models</h2><ul>${list(PROJECT.models)}</ul><h2>Routes</h2><ul>${list(PROJECT.routes)}</ul>` +",
            "      '<p><strong>Status:</strong> Running</p></body></html>'",
            "    );",
            "  }",
            "",
            "  @Get('health')",
            "  async health(@Res({ passthrough: true }) response: Response) {",
            "    let database = 'ok';",
            "    try {",
            "      await this.dataSource.query('SELECT 1');",
            "    } catch {",
            "      database = 'unavailable';",
            "      response.status(503);",
            "    }",
            "    return { status: database === 'ok' ? 'ok' : 'degraded', project: PROJECT.project, database };",
            "  }",
            "",
            "  @Get('routes')",
            "  routes() {",
            "    return { routes: PROJECT.routes };",
            "  }",
            "}",
            "",
        ]
    )


def migration_class(table: dict) -> tuple[str, str]:
    timestamp = MIGRATION_EPOCH + table["sequence"] * 1000
    class_name = f"Create{pascal_case(table['table'])}Table{timestamp}"
    return class_name, f"{timestamp}-create-{table['table'].replace('_', '-')}-table"


def migration_code(table: dict) -> str:
    class_name, _ = migration_class(table)
    columns = ["        { name: 'id', type: 'integer', isPrimary: true, isGenerated: true, generationStrategy: 'increment' },"]
    for column in table["fields"]:
        options = [f"name: {ts_string(column['name'])}", f"type: columnType('{column['type']}') as string"]
        if column["type"] == "STRING":
            options.append("length: '255'")
        options.append(f"isNullable: {'false' if column['required'] else 'true'}")
        if column["unique"]:
            options.append("isUnique: true")
        columns.append(f"        {{ {', '.join(options)} }},")
    for foreign_key in table["foreign_keys"]:
        options = [f"name: {ts_string(foreign_key['column'])}", "type: 'integer'", "isNullable: false"]
        if foreign_key.get("unique"):
            options.append("isUnique: true")
        columns.append(f"        {{ {', '.join(options)} }},")
    columns.extend(
        [
            "        { name: 'created_at', type: columnType('DATETIME') as string, isNullable: false },",
            "        { name: 'updated_at', type: columnType('DATETIME') as string, isNullable: false },",
        ]
    )
    foreign_keys = [
        f"        {{ columnNames: [{ts_string(foreign_key['column'])}], referencedTableName: {ts_string(foreign_key['references_table'])}, referencedColumnNames: ['id'] }},"
        for foreign_key in table["foreign_keys"]
    ]
    indices = [
        f"        {{ columnNames: [{ts_string(foreign_key['column'])}] }},"
        for foreign_key in table["foreign_keys"]
        if not foreign_key.get("unique")
    ]
    table_lines = ["      new Table({", f"        name: {ts_string(table['table'])},", "        columns: ["]
    table_lines.extend("  " + column for column in columns)
    table_lines.append("        ],")
    if foreign_keys:
        table_lines.append("        foreignKeys: [")
        table_lines.extend("  " + entry for entry in foreign_keys)
        table_lines.append("        ],")
    if indices:
        table_lines.append("        indices: [")
        table_lines.extend("  " + entry for entry in indices)
        table_lines.append("        ],")
    table_lines.append("      }),")
    return "\n".join(
        [
            "import { MigrationInterface, QueryRunner, Table } from 'typeorm';",
            "import { columnType } from '../column-types';",
            "",
            f"export class {class_name} implements MigrationInterface {{",
            f"  name = {ts_string(class_name)};",
            "",
            "  async up(queryRunner: QueryRunner): Promise<void> {",
            "    await queryRunner.createTable(",
            *table_lines,
            "    );",
            "  }",
            "",
            "  async down(queryRunner: QueryRunner): Promise<void> {",
            f"    await queryRunner.dropTable({ts_string(table['table'])});",
            "  }",
            "}",
            "",
        ]
    )


def data_source_code(ir: dict) -> str:
    entity_imports = [
        f"import {{ {model['name']} }} from '../modules/{folder(model['name'])}/{file_base(model['name'])}.entity';"
        for model in ir["models"]
    ]
    migrations = [migration_class(table) for table in ir["migrations"]["tables"]]
    migration_imports = [f"import {{ {class_name} }} from './migrations/{file}';" for class_name, file in migrations]
    return "\n".join(
        [
            "import { mkdirSync } from 'fs';",
            "import { dirname } from 'path';",
            "import { DataSource, DataSourceOptions } from 'typeorm';",
            "import { settings, sqlitePath } from '../config/settings';",
            *entity_imports,
            *migration_imports,
            "",
            f"export const ENTITIES = [{', '.join(model['name'] for model in ir['models'])}];",
            f"export const MIGRATIONS = [{', '.join(class_name for class_name, _ in migrations)}];",
            "",
            "export function dataSourceOptions(): DataSourceOptions {",
            "  const common = { entities: ENTITIES, migrations: MIGRATIONS, synchronize: false };",
            "  switch (settings.dbConnection) {",
            "    case 'sqlite': {",
            "      const database = sqlitePath(settings.dbDatabase);",
            "      if (database !== ':memory:') {",
            "        mkdirSync(dirname(database), { recursive: true });",
            "      }",
            "      return { type: 'better-sqlite3', database, ...common };",
            "    }",
            "    case 'mysql':",
            "      return {",
            "        type: 'mysql',",
            "        host: settings.dbHost,",
            "        port: settings.dbPort,",
            "        username: settings.dbUsername,",
            "        password: settings.dbPassword,",
            "        database: settings.dbDatabase,",
            "        timezone: 'Z',",
            "        charset: 'utf8mb4',",
            "        ...common,",
            "      };",
            "    case 'pgsql':",
            "      return {",
            "        type: 'postgres',",
            "        host: settings.dbHost,",
            "        port: settings.dbPort,",
            "        username: settings.dbUsername,",
            "        password: settings.dbPassword,",
            "        database: settings.dbDatabase,",
            "        ...common,",
            "      };",
            "  }",
            "  throw new Error(`Unsupported DB_CONNECTION: ${settings.dbConnection} (use mysql, pgsql or sqlite)`);",
            "}",
            "",
            "export default new DataSource(dataSourceOptions());",
            "",
        ]
    )


def settings_code(ir: dict, settings: dict, port: int) -> str:
    lines = [
        "import { existsSync, readFileSync } from 'fs';",
        "import { isAbsolute, join } from 'path';",
        "",
        "const ROOT = join(__dirname, '..', '..');",
        "",
        "function loadEnvFile(path: string): void {",
        "  if (!existsSync(path)) {",
        "    return;",
        "  }",
        "  for (const rawLine of readFileSync(path, 'utf8').split(/\\r?\\n/)) {",
        "    const line = rawLine.trim();",
        "    if (!line || line.startsWith('#') || !line.includes('=')) {",
        "      continue;",
        "    }",
        "    const index = line.indexOf('=');",
        "    const key = line.slice(0, index).trim();",
        "    if (process.env[key] === undefined) {",
        "      process.env[key] = line.slice(index + 1).trim().replace(/^['\"]|['\"]$/g, '');",
        "    }",
        "  }",
        "}",
        "",
        "loadEnvFile(join(ROOT, '.env'));",
        "",
        "function env(key: string, fallback = ''): string {",
        "  const value = process.env[key];",
        "  return value === undefined || value === '' ? fallback : value;",
        "}",
        "",
        "export function sqlitePath(path: string): string {",
        "  return path === ':memory:' || isAbsolute(path) ? path : join(ROOT, path);",
        "}",
        "",
        "export const settings = {",
        f"  appName: env('APP_NAME', {ts_string(ir['project'])}),",
        f"  port: Number(env('PORT', '{port}')),",
        f"  dbConnection: env('DB_CONNECTION', {ts_string(settings['connection'])}),",
        "  dbHost: env('DB_HOST', '127.0.0.1'),",
        f"  dbPort: Number(env('DB_PORT', {ts_string(settings['port'] or '3306')})),",
        f"  dbDatabase: env('DB_DATABASE', {ts_string(settings['database'])}),",
        f"  dbUsername: env('DB_USERNAME', {ts_string(settings['username'])}),",
        "  dbPassword: env('DB_PASSWORD', ''),",
        "  corsOrigins: env('CORS_ORIGINS', '*').split(',').map((origin) => origin.trim()).filter(Boolean),",
    ]
    if ir.get("auth"):
        lines.extend(
            [
                "  jwtSecret: env('JWT_SECRET', ''),",
                f"  jwtTtl: Number(env('JWT_TTL', '{ir['auth']['token_ttl_seconds']}')),",
            ]
        )
    lines.extend(["};", ""])
    return "\n".join(lines)
