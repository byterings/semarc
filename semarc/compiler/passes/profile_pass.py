from pathlib import Path

from semarc.architecture.profiles import (
    ProfileCompositionError,
    ProfileCompositionResolver,
    ProfileLoader,
    ProfileLoadingError,
)
from semarc.validator.validator import SemanticValidationError


class ProfilePass:
    """Loads profile metadata and resolves profile-composed modules."""

    def run(self, context) -> None:
        context.compiler_passes.append("ProfilePass")
        try:
            registry = ProfileLoader(self._profiles_dir()).load_all()
            profiles, modules = ProfileCompositionResolver(registry).resolve(
                [profile.name for profile in context.ast.profiles]
            )
        except ProfileLoadingError as error:
            raise SemanticValidationError(f"[Semantic Error]\n{error}") from error
        except ProfileCompositionError as error:
            raise SemanticValidationError(f"[Semantic Error]\n{error}") from error

        context.loaded_profiles = profiles
        context.resolved_profile_modules = modules

    def _profiles_dir(self) -> Path:
        return Path(__file__).resolve().parents[2] / "profiles"
