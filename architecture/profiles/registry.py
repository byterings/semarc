from architecture.profiles.profile import Profile


class ProfileRegistry:
    """Stores profile metadata without applying compiler behavior."""

    def __init__(self) -> None:
        self._profiles: dict[str, Profile] = {}

    def register(self, profile: Profile) -> None:
        self._profiles[profile.name.upper()] = profile

    def get(self, name: str) -> Profile | None:
        return self._profiles.get(name.upper())

    def all(self) -> list[Profile]:
        return [self._profiles[name] for name in sorted(self._profiles)]
