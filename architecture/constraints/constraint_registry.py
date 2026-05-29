from architecture.constraints.rules.architecture_constraints import ArchitectureCompletenessRule
from architecture.constraints.rules.auth_constraints import ConflictingAuthStrategiesRule, JwtRateLimitRule
from architecture.constraints.rules.database_constraints import MissingDatabaseRule, SqliteRedisRule
from architecture.constraints.rules.relationship_constraints import RelationshipDepthRule
from architecture.constraints.rules.route_constraints import LoginValidationRecommendationRule


class ConstraintRegistry:
    """Central registry for deterministic architecture constraint rules."""

    def __init__(self) -> None:
        self.rules = []

    def register_constraint(self, rule) -> None:
        self.rules.append(rule)

    def load_defaults(self) -> None:
        self.register_constraint(ConflictingAuthStrategiesRule())
        self.register_constraint(JwtRateLimitRule())
        self.register_constraint(MissingDatabaseRule())
        self.register_constraint(SqliteRedisRule())
        self.register_constraint(RelationshipDepthRule())
        self.register_constraint(LoginValidationRecommendationRule())
        self.register_constraint(ArchitectureCompletenessRule())
