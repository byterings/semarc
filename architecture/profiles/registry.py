from architecture.profiles.profile import Profile


class ProfileRegistry:
    """Stores profile metadata without applying compiler behavior."""

    def __init__(self) -> None:
        self._profiles: dict[str, Profile] = {}

    def register(self, profile: Profile) -> None:
        self._profiles[self._key(profile.name)] = profile

    def get(self, name: str) -> Profile | None:
        return self._profiles.get(self._key(name))

    def all(self) -> list[Profile]:
        return [self._profiles[name] for name in sorted(self._profiles)]

    def _key(self, value: str) -> str:
        return "".join(char for char in value.upper() if char.isalnum())
