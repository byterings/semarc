from typing import List

from semarc.ast_loader import load_ast_builder, load_semantic_nodes
from semarc.lexer.lexer import DEFAULT_MODIFIER, FIELD_MODIFIERS, RESERVED_KEYWORDS, ROUTE_ACCESS, VALIDATION_RULES, Token

nodes = load_semantic_nodes()
ast_builder = load_ast_builder()
ArchitectureNode = nodes.ArchitectureNode
AuthNode = nodes.AuthNode
DatabaseNode = nodes.DatabaseNode
FieldNode = nodes.FieldNode
ModelNode = nodes.ModelNode
PackageNode = nodes.PackageNode
ProfileNode = nodes.ProfileNode
ProjectNode = nodes.ProjectNode
RelationNode = nodes.RelationNode
RouteNode = nodes.RouteNode
TargetNode = nodes.TargetNode
ValidationNode = nodes.ValidationNode
AstBuilder = ast_builder.AstBuilder


class ParserError(Exception):
    pass


LEGACY_MIN_LENGTH = 6


class Parser:
    """Builds a semantic AST from tokens without generating target code."""

    def __init__(self) -> None:
        self.builder = AstBuilder()

    def parse(self, token_lines: List[List[Token]]) -> ArchitectureNode:
        project = None
        target = None
        database = None
        auth = None
        auth_declarations: List[AuthNode] = []
        profiles: List[ProfileNode] = []
        packages: List[PackageNode] = []
        models: List[ModelNode] = []
        routes: List[RouteNode] = []
        relations: List[RelationNode] = []
        validations: List[ValidationNode] = []
        current_model = None

        for tokens in token_lines:
            first = tokens[0]

            if first.indent > 0:
                if current_model is None:
                    raise ParserError(self._message(first, "Field declared outside a model"))
                current_model.fields.append(self._parse_field(tokens))
                continue

            current_model = None

            if first.token_type != "KEYWORD":
                raise ParserError(self._message(first, "Expected a semantic command"))

            command = first.value.upper()

            if command == "PROJECT":
                project = self._parse_project(tokens)
            elif command == "TARGET":
                target = self._parse_target(tokens)
            elif command == "PROFILE":
                profiles.append(self._parse_profile(tokens))
            elif command == "USE":
                packages.append(self._parse_use(tokens))
            elif command == "DATABASE":
                database = self._parse_database(tokens)
            elif command == "AUTH":
                auth = self._parse_auth(tokens)
                auth_declarations.append(auth)
            elif command == "MODEL":
                current_model = self._parse_model(tokens)
                models.append(current_model)
            elif command == "ROUTE":
                routes.append(self._parse_route(tokens))
            elif command == "RELATION":
                relations.append(self._parse_relation(tokens))
            elif command == "VALIDATE":
                validations.append(self._parse_validation(tokens))
            elif command in RESERVED_KEYWORDS:
                raise ParserError(
                    self._message(first, f"{command} is reserved for a future SEMARC version and is not supported yet")
                )
            else:
                raise ParserError(self._message(first, f"Unsupported command {first.value}"))

        architecture = self.builder.architecture(
            project,
            target,
            database,
            auth,
            models,
            routes,
            relations,
            validations,
            profiles,
            packages,
        )
        architecture.metadata["auth_strategies"] = [node.strategy for node in auth_declarations]
        return architecture

    def _parse_project(self, tokens: List[Token]) -> ProjectNode:
        self._expect_length(tokens, 2, "PROJECT requires a project name")
        self._expect(tokens[1], "IDENTIFIER", "PROJECT name must be an identifier")
        return self.builder.project(tokens[1].value, tokens[0])

    def _parse_target(self, tokens: List[Token]) -> TargetNode:
        self._expect_length(tokens, 2, "TARGET requires a target profile")
        self._expect(tokens[1], "IDENTIFIER", "TARGET profile must be an identifier")
        return self.builder.target(tokens[1].value, tokens[0])

    def _parse_profile(self, tokens: List[Token]) -> ProfileNode:
        self._expect_length(tokens, 2, "PROFILE requires a profile name")
        self._expect(tokens[1], "IDENTIFIER", "PROFILE name must be an identifier")
        return self.builder.profile(tokens[1].value, tokens[0])

    def _parse_use(self, tokens: List[Token]) -> PackageNode:
        self._expect_length(tokens, 2, "USE requires a package name")
        self._expect(tokens[1], "IDENTIFIER", "USE package must be an identifier")
        return self.builder.package(tokens[1].value, tokens[0])

    def _parse_database(self, tokens: List[Token]) -> DatabaseNode:
        self._expect_length(tokens, 2, "DATABASE requires an engine")
        self._expect(tokens[1], "IDENTIFIER", "DATABASE engine must be an identifier")
        return self.builder.database(tokens[1].value, tokens[0])

    def _parse_auth(self, tokens: List[Token]) -> AuthNode:
        self._expect_length(tokens, 2, "AUTH requires a strategy")
        self._expect(tokens[1], "IDENTIFIER", "AUTH strategy must be an identifier")
        return self.builder.auth(tokens[1].value, tokens[0])

    def _parse_model(self, tokens: List[Token]) -> ModelNode:
        self._expect_length(tokens, 2, "MODEL requires a model name")
        self._expect(tokens[1], "IDENTIFIER", "MODEL name must be an identifier")
        return self.builder.model(tokens[1].value, tokens[0])

    def _parse_field(self, tokens: List[Token]) -> FieldNode:
        if len(tokens) < 2:
            raise ParserError(self._message(tokens[0], "Model field requires a name and type"))
        if tokens[0].token_type not in {"IDENTIFIER", "KEYWORD"}:
            raise ParserError(self._message(tokens[0], "Field name must be an identifier"))
        self._expect(tokens[1], "TYPE", "Field type must be a supported semantic type")
        modifiers = []
        default = None
        index = 2
        while index < len(tokens):
            token = tokens[index]
            index += 1
            if token.value == DEFAULT_MODIFIER:
                if default is not None:
                    raise ParserError(self._message(token, "DEFAULT is declared twice"))
                if index >= len(tokens):
                    raise ParserError(self._message(token, "DEFAULT requires a value, for example DEFAULT draft"))
                default = tokens[index].value
                index += 1
                continue
            if token.value not in FIELD_MODIFIERS:
                supported = ", ".join(sorted(FIELD_MODIFIERS | {DEFAULT_MODIFIER}))
                raise ParserError(self._message(token, f"Field modifier must be one of: {supported}"))
            modifiers.append(token.value)
        return self.builder.field(tokens[0].value, tokens[1].value, tokens[0], modifiers, default)

    def _parse_route(self, tokens: List[Token]) -> RouteNode:
        if len(tokens) < 3:
            raise ParserError(self._message(tokens[0], "ROUTE requires an HTTP method and a path"))
        self._expect(tokens[1], "HTTP_METHOD", "ROUTE method must be an HTTP method")
        self._expect(tokens[2], "STRING", "ROUTE path must start with /")
        rest = tokens[3:]
        access = None
        if rest and rest[0].value in ROUTE_ACCESS:
            access = rest[0].value
            rest = rest[1:]
        roles: list[str] = []
        if rest:
            if rest[0].value != "ROLE":
                raise ParserError(self._message(rest[0], "ROUTE options are PUBLIC, PROTECTED and ROLE name [name ...]"))
            if len(rest) == 1:
                raise ParserError(self._message(rest[0], "ROLE requires at least one role name"))
            roles = [token.value for token in rest[1:]]
        return self.builder.route(tokens[1].value, tokens[2].value, tokens[0], access, roles)

    def _parse_relation(self, tokens: List[Token]) -> RelationNode:
        self._expect_length(tokens, 4, "RELATION requires source model, relation type, and target model")
        self._expect(tokens[1], "IDENTIFIER", "RELATION source must be a model identifier")
        self._expect(tokens[2], "RELATION_TYPE", "RELATION type must be supported")
        self._expect(tokens[3], "IDENTIFIER", "RELATION target must be a model identifier")
        return self.builder.relation(tokens[1].value, tokens[2].value, tokens[3].value, tokens[0])

    def _parse_validation(self, tokens: List[Token]) -> ValidationNode:
        if len(tokens) < 3:
            raise ParserError(self._message(tokens[0], "VALIDATE requires a field and at least one rule"))
        self._expect(tokens[1], "IDENTIFIER", "VALIDATE field must be an identifier")
        model_name, field_name = self._validation_target(tokens[1])

        rules: list[str] = []
        parameters: dict[str, int] = {}
        values: list[str] = []
        index = 2
        while index < len(tokens):
            token = tokens[index]
            rule = token.value.upper()
            if rule not in VALIDATION_RULES:
                supported = ", ".join(sorted(VALIDATION_RULES))
                raise ParserError(self._message(token, f"VALIDATE rule must be one of: {supported}"))
            rules.append(rule)
            index += 1

            if rule == "IN":
                values = [item.value for item in tokens[index:]]
                if not values:
                    raise ParserError(self._message(token, "IN requires the allowed values, for example IN draft published"))
                break

            if rule in {"MIN", "MAX"}:
                if index < len(tokens) and tokens[index].token_type == "NUMBER":
                    parameters[rule] = int(tokens[index].value)
                    index += 1
                elif rule == "MIN":
                    parameters[rule] = LEGACY_MIN_LENGTH
                else:
                    raise ParserError(self._message(token, "MAX requires a numeric value, for example MAX 255"))

        return self.builder.validation(field_name, rules, tokens[0], model_name, parameters, values)

    def _validation_target(self, token: Token) -> tuple[str | None, str]:
        if "." not in token.value:
            return None, token.value
        parts = token.value.split(".")
        if len(parts) != 2 or not all(parts):
            raise ParserError(self._message(token, "VALIDATE target must be field or Model.field"))
        return parts[0], parts[1]

    def _expect_length(self, tokens: List[Token], expected: int, message: str) -> None:
        if len(tokens) != expected:
            raise ParserError(self._message(tokens[0], message))

    def _expect(self, token: Token, token_type: str, message: str) -> None:
        if token.token_type != token_type:
            raise ParserError(self._message(token, message))

    def _message(self, token: Token, message: str) -> str:
        return f"Line {token.line}, column {token.column}: {message}"
