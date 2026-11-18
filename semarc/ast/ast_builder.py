from semarc.ast_loader import load_semantic_nodes


nodes = load_semantic_nodes()
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
SourceLocation = nodes.SourceLocation
TargetNode = nodes.TargetNode
ValidationNode = nodes.ValidationNode


class AstBuilder:
    """Centralized AST construction so parser code stays focused on grammar."""

    def project(self, name: str, token) -> ProjectNode:
        return ProjectNode(name=name, location=self._location(token))

    def target(self, name: str, token) -> TargetNode:
        return TargetNode(name=name.upper(), location=self._location(token))

    def profile(self, name: str, token) -> ProfileNode:
        return ProfileNode(name=name, location=self._location(token))

    def package(self, name: str, token) -> PackageNode:
        return PackageNode(name=name, location=self._location(token))

    def database(self, engine: str, token) -> DatabaseNode:
        return DatabaseNode(engine=engine.upper(), location=self._location(token))

    def auth(self, strategy: str, token) -> AuthNode:
        return AuthNode(strategy=strategy.upper(), location=self._location(token))

    def model(self, name: str, token) -> ModelNode:
        return ModelNode(name=name, location=self._location(token))

    def field(self, name: str, field_type: str, token, modifiers: list[str] | None = None) -> FieldNode:
        return FieldNode(
            name=name,
            field_type=field_type.upper(),
            modifiers=[modifier.upper() for modifier in modifiers or []],
            location=self._location(token),
        )

    def route(self, method: str, path: str, token, access: str | None = None) -> RouteNode:
        return RouteNode(
            method=method.upper(),
            path=path,
            access=access.upper() if access else None,
            location=self._location(token),
        )

    def relation(self, source_model: str, relation_type: str, target_model: str, token) -> RelationNode:
        return RelationNode(
            source_model=source_model,
            relation_type=relation_type.upper(),
            target_model=target_model,
            location=self._location(token),
        )

    def validation(
        self,
        field_name: str,
        rules: list[str],
        token,
        model_name: str | None = None,
        parameters: dict[str, int] | None = None,
    ) -> ValidationNode:
        return ValidationNode(
            field_name=field_name,
            rules=[rule.upper() for rule in rules],
            model_name=model_name,
            parameters={key.upper(): value for key, value in (parameters or {}).items()},
            location=self._location(token),
        )

    def architecture(
        self,
        project,
        target,
        database,
        auth,
        models,
        routes,
        relations,
        validations,
        profiles=None,
        packages=None,
    ) -> ArchitectureNode:
        return ArchitectureNode(
            project=project,
            target=target,
            database=database,
            auth=auth,
            models=models,
            routes=routes,
            relations=relations,
            validations=validations,
            profiles=profiles or [],
            packages=packages or [],
            location=project.location if project else SourceLocation(),
        )

    def _location(self, token) -> SourceLocation:
        return SourceLocation(line=token.line, column=token.column)
