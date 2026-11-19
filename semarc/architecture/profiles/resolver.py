from semarc.architecture.profiles.profile import Profile
from semarc.architecture.profiles.registry import ProfileRegistry


class ProfileCompositionError(Exception):
    def __init__(self, code: str, message: str, chain: list[str] | None = None) -> None:
        chain_text = "\n" + "\n-> ".join(chain) if chain else ""
        super().__init__(f"{code} {message}{chain_text}")
        self.code = code
        self.chain = chain or []


class ProfileCompositionResolver:
    """Resolves profile modules including inherited profile composition."""

    def __init__(self, registry: ProfileRegistry) -> None:
        self.registry = registry

    def resolve(self, profile_names: list[str]) -> tuple[list[Profile], list[str]]:
        resolved_profiles: list[Profile] = []
        resolved_profile_keys: set[str] = set()
        resolved_modules: list[str] = []
        resolved_module_keys: set[str] = set()

        for profile_name in profile_names:
            profile = self.registry.get(profile_name)
            if profile is None:
                raise ProfileCompositionError("SEM8001", f"Unknown profile: {profile_name}")
            self._visit(
                profile,
                [],
                resolved_profiles,
                resolved_profile_keys,
                resolved_modules,
                resolved_module_keys,
            )

        return resolved_profiles, resolved_modules

    def _visit(
        self,
        profile: Profile,
        stack: list[str],
        resolved_profiles: list[Profile],
        resolved_profile_keys: set[str],
        resolved_modules: list[str],
        resolved_module_keys: set[str],
    ) -> None:
        profile_key = profile.name.upper()
        stack_keys = [name.upper() for name in stack]
        if profile_key in stack_keys:
            cycle_start = stack_keys.index(profile_key)
            cycle = stack[cycle_start:] + [profile.name]
            raise ProfileCompositionError("SEM8002", "Circular profile inheritance", cycle)

        stack.append(profile.name)
        for parent_name in profile.extends:
            parent = self.registry.get(parent_name)
            if parent is None:
                raise ProfileCompositionError("SEM8001", f"Unknown profile: {parent_name}", stack + [parent_name])
            self._visit(
                parent,
                stack,
                resolved_profiles,
                resolved_profile_keys,
                resolved_modules,
                resolved_module_keys,
            )
        stack.pop()

        if profile_key not in resolved_profile_keys:
            resolved_profiles.append(profile)
            resolved_profile_keys.add(profile_key)

        for module_name in profile.modules:
            module_key = module_name.lower()
            if module_key in resolved_module_keys:
                continue
            resolved_module_keys.add(module_key)
            resolved_modules.append(module_name)
