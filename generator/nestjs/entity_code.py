"""Renders TypeORM entities, class-validator DTOs, repositories, services and modules."""
from generator.nestjs.typescript import TS_TYPES, Imports, file_base, folder, ts_string
from generator.utils.resource_views import field_rules, output_fields, owner_reference, secret_fields, unique_columns


def entity_code(model: dict, reserved: set[str]) -> str:
    imports = Imports(reserved)
    entity = imports.use("typeorm", "Entity")
    column = imports.use("typeorm", "Column")
    primary = imports.use("typeorm", "PrimaryGeneratedColumn")
    imports.use("../../database/column-types", "columnType")

    body = [f"@{entity}({{ name: {ts_string(model['table'])} }})", f"export class {model['name']} {{"]
    body.extend([f"  @{primary}({{ type: 'integer' }})", "  id!: number;", ""])
    for model_field in model["fields"]:
        options = [f"type: columnType('{model_field['type']}')"]
        if model_field["type"] == "STRING":
            options.append("length: 255")
        if not model_field["required"]:
            options.append("nullable: true")
        if model_field["unique"]:
            options.append("unique: true")
        annotation = TS_TYPES[model_field["type"]] + ("" if model_field["required"] else " | null")
        body.extend([f"  @{column}({{ {', '.join(options)} }})", f"  {model_field['name']}!: {annotation};", ""])
    for reference in model["references"]:
        options = ["type: columnType('INTEGER')"]
        if reference["unique"]:
            options.append("unique: true")
        decorators = [f"  @{column}({{ {', '.join(options)} }})"]
        if not reference["unique"]:
            decorators.insert(0, f"  @{imports.use('typeorm', 'Index')}()")
        body.extend(decorators + [f"  {reference['column']}!: number;", ""])
    body.extend(
        [
            f"  @{column}({{ type: columnType('DATETIME') }})",
            "  created_at!: Date;",
            "",
            f"  @{column}({{ type: columnType('DATETIME') }})",
            "  updated_at!: Date;",
            "}",
            "",
        ]
    )
    relations = [f"// Relation metadata: {relation['source']} {relation['type']} {relation['target']}" for relation in model["relations"]]
    return "\n".join(imports.render() + [""] + (relations + [""] if relations else []) + body)


def dto_code(model: dict, reserved: set[str], partial: bool) -> str:
    imports = Imports(reserved)
    name = f"{'Update' if partial else 'Create'}{model['name']}Dto"
    lines = [f"export class {name} {{"]
    owner = owner_reference(model)

    for model_field in model["fields"]:
        rules = field_rules(model_field)
        decorators = _presence(imports, name, model_field["name"], rules["required"], partial)
        decorators.extend(_type_decorators(imports, model_field["name"], rules))
        optional = partial or not rules["required"]
        annotation = TS_TYPES[rules["type"]] + (" | null" if not rules["required"] else "")
        lines.extend(decorators + [f"  {model_field['name']}{'?' if optional else '!'}: {annotation};", ""])

    for reference in model["references"]:
        required = reference is not owner
        decorators = _presence(imports, name, reference["column"], required, partial or reference is owner)
        decorators.extend([f"  @{imports.use('class-validator', 'IsInt')}()", f"  @{imports.use('class-validator', 'Min')}(1)"])
        if reference is owner:
            decorators.insert(0, "  // Taken from the bearer token on protected routes.")
        optional = partial or not required
        lines.extend(decorators + [f"  {reference['column']}{'?' if optional else '!'}: number;", ""])

    if lines[-1] == "":
        lines.pop()
    lines.extend(["}", ""])
    return "\n".join(imports.render() + [""] + lines)


def _presence(imports: Imports, dto: str, field_name: str, required: bool, partial: bool) -> list[str]:
    if required and not partial:
        return [f"  @{imports.use('class-validator', 'IsDefined')}()"]
    if required and partial:
        validate_if = imports.use("class-validator", "ValidateIf")
        return [f"  @{validate_if}((dto: {dto}) => dto.{field_name} !== undefined)"]
    return [f"  @{imports.use('class-validator', 'IsOptional')}()"]


def _type_decorators(imports: Imports, field_name: str, rules: dict) -> list[str]:
    decorators = []
    field_type = rules["type"]
    if field_type in {"STRING", "TEXT"}:
        decorators.append(f"  @{imports.use('class-validator', 'IsString')}()")
        if rules["not_empty"]:
            decorators.append(f"  @{imports.use('class-validator', 'Matches')}(/\\S/, {{ message: '{field_name} must not be empty' }})")
        if rules["email"]:
            decorators.append(f"  @{imports.use('class-validator', 'IsEmail')}({{}}, {{ message: '{field_name} must be a valid email address' }})")
        if rules["min"] is not None:
            decorators.append(f"  @{imports.use('class-validator', 'MinLength')}({rules['min']})")
        if rules["max"] is not None:
            decorators.append(f"  @{imports.use('class-validator', 'MaxLength')}({rules['max']})")
    elif field_type in {"INTEGER", "FLOAT"}:
        check = "IsInt" if field_type == "INTEGER" else "IsNumber"
        decorators.append(f"  @{imports.use('class-validator', check)}()")
        if rules["min"] is not None:
            decorators.append(f"  @{imports.use('class-validator', 'Min')}({rules['min']})")
        if rules["max"] is not None:
            decorators.append(f"  @{imports.use('class-validator', 'Max')}({rules['max']})")
    else:
        decorators.append(f"  @{imports.use('class-validator', 'IsBoolean')}()")
    return decorators


def repository_code(model: dict, reserved: set[str]) -> str:
    name = model["name"]
    imports = Imports(reserved)
    injectable = imports.use("@nestjs/common", "Injectable")
    inject = imports.use("@nestjs/typeorm", "InjectRepository")
    repository = imports.use("typeorm", "Repository")
    imports.use("../../common/resource.repository", "ResourceRepository")
    imports.use(f"./{file_base(name)}.entity", name)
    return "\n".join(
        imports.render()
        + [
            "",
            f"@{injectable}()",
            f"export class {name}Repository extends ResourceRepository<{name}> {{",
            f"  constructor(@{inject}({name}) repository: {repository}<{name}>) {{",
            "    super(repository);",
            "  }",
            "}",
            "",
        ]
    )


def service_code(model: dict, reserved: set[str]) -> str:
    name = model["name"]
    imports = Imports(reserved)
    injectable = imports.use("@nestjs/common", "Injectable")
    imports.use("../../common/resource.service", "ResourceService")
    imports.use(f"./{file_base(name)}.entity", name)
    imports.use(f"./{folder(name)}.repository", f"{name}Repository")
    secrets = secret_fields(model)

    lines = [f"@{injectable}()", f"export class {name}Service extends ResourceService<{name}> {{"]
    lines.append(f"  protected readonly name = {ts_string(name)};")
    lines.append(f"  protected readonly output = [{', '.join(ts_string(field) for field, _ in output_fields(model))}];")
    if model["references"]:
        imports.use("../../common/resource.service", "Reference")
        entries = [
            f"{{ column: {ts_string(reference['column'])}, table: {ts_string(reference['table'])}, model: {ts_string(reference['model'])}"
            + (", owner: true" if reference["owner"] else "")
            + " }"
            for reference in model["references"]
        ]
        lines.append(f"  protected readonly references: Reference[] = [{', '.join(entries)}];")
    if model["dependents"]:
        imports.use("../../common/resource.service", "Dependent")
        entries = [
            f"{{ table: {ts_string(dependent['table'])}, column: {ts_string(dependent['column'])}, model: {ts_string(dependent['model'])} }}"
            for dependent in model["dependents"]
        ]
        lines.append(f"  protected readonly dependents: Dependent[] = [{', '.join(entries)}];")
    unique = unique_columns(model)
    if unique:
        lines.append(f"  protected readonly unique = [{', '.join(ts_string(column) for column in unique)}];")

    lines.append("")
    if secrets:
        imports.use("../../common/password-hasher", "PasswordHasher")
        lines.extend(
            [
                "  constructor(",
                f"    repository: {name}Repository,",
                "    private readonly hasher: PasswordHasher,",
                "  ) {",
                "    super(repository);",
                "  }",
                "",
                "  protected async beforeWrite(data: Record<string, unknown>): Promise<Record<string, unknown>> {",
            ]
        )
        for secret in secrets:
            lines.extend(
                [
                    f"    if (typeof data.{secret} === 'string') {{",
                    f"      data.{secret} = await this.hasher.hash(data.{secret});",
                    "    }",
                ]
            )
        lines.extend(["    return data;", "  }"])
    else:
        lines.extend([f"  constructor(repository: {name}Repository) {{", "    super(repository);", "  }"])
    lines.extend(["}", ""])
    return "\n".join(imports.render() + [""] + lines)


def module_code(model: dict, reserved: set[str], has_controller: bool) -> str:
    name = model["name"]
    imports = Imports(reserved)
    module = imports.use("@nestjs/common", "Module")
    typeorm = imports.use("@nestjs/typeorm", "TypeOrmModule")
    imports.use(f"./{file_base(name)}.entity", name)
    imports.use(f"./{folder(name)}.repository", f"{name}Repository")
    imports.use(f"./{folder(name)}.service", f"{name}Service")
    providers = [f"{name}Repository", f"{name}Service"]
    if secret_fields(model):
        imports.use("../../common/password-hasher", "PasswordHasher")
        providers.append("PasswordHasher")
    lines = [f"@{module}({{", f"  imports: [{typeorm}.forFeature([{name}])],"]
    if has_controller:
        imports.use(f"./{folder(name)}.controller", f"{name}Controller")
        lines.append(f"  controllers: [{name}Controller],")
    lines.extend(
        [
            f"  providers: [{', '.join(providers)}],",
            f"  exports: [{', '.join(providers)}],",
            "})",
            f"export class {name}Module {{}}",
            "",
        ]
    )
    return "\n".join(imports.render() + [""] + lines)
