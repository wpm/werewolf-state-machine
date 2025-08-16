from __future__ import annotations

"""Domain model representing the complete Werewolf game state."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, computed_field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class Phase(StrEnum):
    """Game phases."""

    NIGHT = "night"
    DAY = "day"


class Role(StrEnum):
    """Roles that players may take."""

    WEREWOLF = "werewolf"
    SEER = "seer"
    VILLAGER = "villager"
    DOCTOR = "doctor"


class Winner(StrEnum):
    """Final game state."""

    WEREWOLVES = "werewolves"
    VILLAGERS = "villagers"
    NONE = "none"


PlayerId = str


class WerewolfState(BaseModel):
    """Pydantic model holding the entire game state."""

    day: int = 1
    phase: Phase = Phase.NIGHT
    roles: dict[PlayerId, Role]
    alive_players: set[PlayerId] | None = None
    known_roles: dict[PlayerId, dict[PlayerId, Role]] = {}

    def model_post_init(self, __context: Any) -> None:
        """Default ``alive_players`` to all players if not provided."""
        if self.alive_players is None:
            self.alive_players = set(self.roles.keys())

    @computed_field
    @property
    def winner(self) -> Winner:
        """Determine the current winner.

        Villagers win when no werewolves remain alive. Werewolves win when
        their count is equal to or exceeds the number of non-werewolf players
        still alive. Otherwise, no side has won yet.
        """
        alive_roles = [self.roles[player] for player in self.alive_players]
        werewolves = sum(1 for role in alive_roles if role == Role.WEREWOLF)
        non_werewolves = len(alive_roles) - werewolves

        if werewolves == 0:
            return Winner.VILLAGERS
        if werewolves >= non_werewolves:
            return Winner.WEREWOLVES
        return Winner.NONE
