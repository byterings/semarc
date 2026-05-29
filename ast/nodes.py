from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SourceLocation:
    """Source position used for readable compiler errors and debugging."""

    line: int = 0
    column: int = 0


class AstNode:
    """Base class for semantic AST nodes.

    AST nodes describe architecture intent only. They do not know about PHP,
    folders, templates, or any target runtime.
    """

    location: SourceLocation
    metadata: Dict[str, Any]

    def debug(self) -> Dict[str, Any]:
        values = {
            key: value
            for key, value in self.__dict__.items()
            if key not in {"location", "metadata"}
        }
        values["location"] = {
            "line": self.location.line,
            "column": self.location.column,
        }
        values["metadata"] = self.metadata
        return values


@dataclass(frozen=True)
class ProjectNode(AstNode):
    """Semantic project identity."""

    name: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TargetNode(AstNode):
    """Requested backend target profile."""

    name: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileNode(AstNode):
    """Future semantic profile selection.

    Profiles are metadata-only in the current compiler and must not change
    generation behavior until a dedicated profile pass is introduced.
    """

    name: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PackageNode(AstNode):
    """Future semantic package reference from USE declarations."""

    name: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DatabaseNode(AstNode):
    """Database architecture intent, independent of implementation code."""

    engine: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuthNode(AstNode):
    """Authentication architecture intent."""

    strategy: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FieldNode(AstNode):
    """A semantic model field."""

    name: str
    field_type: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelNode(AstNode):
    """A semantic domain model."""

    name: str
    fields: List[FieldNode] = field(default_factory=list)
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RouteNode(AstNode):
    """A semantic HTTP endpoint declaration."""

    method: str
    path: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationNode(AstNode):
    """Semantic model relationship."""

    source_model: str
    relation_type: str
    target_model: str
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationNode(AstNode):
    """Semantic validation intent for an input field."""

    field_name: str
    rules: List[str] = field(default_factory=list)
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ArchitectureNode(AstNode):
    """Root semantic architecture tree produced by the parser."""

    project: Optional[ProjectNode] = None
    target: Optional[TargetNode] = None
    database: Optional[DatabaseNode] = None
    auth: Optional[AuthNode] = None
    models: List[ModelNode] = field(default_factory=list)
    routes: List[RouteNode] = field(default_factory=list)
    relations: List[RelationNode] = field(default_factory=list)
    validations: List[ValidationNode] = field(default_factory=list)
    profiles: List[ProfileNode] = field(default_factory=list)
    packages: List[PackageNode] = field(default_factory=list)
    location: SourceLocation = field(default_factory=SourceLocation)
    metadata: Dict[str, Any] = field(default_factory=dict)
