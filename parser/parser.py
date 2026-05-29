from typing import List

from ast_loader import load_ast_builder, load_semantic_nodes
from lexer.lexer import Token

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
        self._expect_length(tokens, 2, "Model field requires a name and type")
        self._expect(tokens[0], "IDENTIFIER", "Field name must be an identifier")
        self._expect(tokens[1], "TYPE", "Field type must be a supported semantic type")
        return self.builder.field(tokens[0].value, tokens[1].value, tokens[0])

    def _parse_route(self, tokens: List[Token]) -> RouteNode:
        self._expect_length(tokens, 3, "ROUTE requires an HTTP method and path")
        self._expect(tokens[1], "HTTP_METHOD", "ROUTE method must be an HTTP method")
        self._expect(tokens[2], "STRING", "ROUTE path must start with /")
        return self.builder.route(tokens[1].value, tokens[2].value, tokens[0])

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
        for token in tokens[2:]:
            if token.value.upper() not in {"REQUIRED", "EMAIL", "MIN"}:
                raise ParserError(self._message(token, "VALIDATE rule must be supported"))
        return self.builder.validation(tokens[1].value, [token.value for token in tokens[2:]], tokens[0])

    def _expect_length(self, tokens: List[Token], expected: int, message: str) -> None:
        if len(tokens) != expected:
            raise ParserError(self._message(tokens[0], message))

    def _expect(self, token: Token, token_type: str, message: str) -> None:
        if token.token_type != token_type:
            raise ParserError(self._message(token, message))

    def _message(self, token: Token, message: str) -> str:
        return f"Line {token.line}, column {token.column}: {message}"
