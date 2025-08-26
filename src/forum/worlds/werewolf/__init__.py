"""
Werewolf is a social deduction game where players are secretly assigned roles as villagers, werewolves, or special
characters. Gameplay alternates between night and day phases. During night phases, werewolves eliminate villagers,
while during day phases, all players debate and vote to eliminate suspected werewolves. The game continues until either
all werewolves are eliminated (villagers win) or werewolves outnumber villagers (werewolves win).
"""

__version__ = "0.1.0"

from copy import copy
from enum import StrEnum
from random import shuffle
from typing import Optional, Annotated, Self, Iterator, Union

from annotated_types import Ge
from pydantic import PositiveInt, computed_field, model_validator, Field

from forum.messaging.message import Message

AgentIndex = Annotated[int, Field(ge=0)]


class Phase(StrEnum):
    Start = "Start"
    Night = "Night"
    Day = "Day"
    End = "End"


class Role(StrEnum):
    Werewolf = "Werewolf"
    Villager = "Villager"
    Seer = "Seer"
    Doctor = "Doctor"


class Team(StrEnum):
    Werewolves = "Werewolves"
    Villagers = "Villagers"

    @property
    def roles(self) -> set[Role]:
        return (
            {Role.Werewolf}
            if self is Team.Werewolves
            else {Role.Villager, Role.Seer, Role.Doctor}
        )


class Observation(Message):
    day: PositiveInt
    phase: Phase
    alive: list[bool]
    known_role: dict[AgentIndex, Role]
    voted: list[dict[AgentIndex, Optional[AgentIndex]]]

    def survivors(self) -> set[AgentIndex]:
        return {i for i, alive in enumerate(self.alive) if alive}

    def __str__(self) -> str:
        return f"{self.phase} {self.day}, " + ", ".join(
            [
                f"{index}. {self.known_role.get(index, '?')}{'' if self.alive[index] else '†'}"
                for index, alive in enumerate(self.alive)
            ]
        )


class Action(Message):
    selector: AgentIndex
    selected: AgentIndex

    def __str__(self) -> str:
        return f"{self.selector} → {self.selected}"


class Werewolf(Message):
    day: PositiveInt = 1
    phase: Phase = Phase.Start
    roles: tuple[Role, ...]
    alive: list[bool]
    known_identity: dict[AgentIndex, set[AgentIndex]]
    voted: list[dict[AgentIndex, Optional[AgentIndex]]] = []

    @computed_field
    @property
    def winner(self) -> Optional[Team]:
        werewolves = len(self.survivors(Team.Werewolves))
        if werewolves == 0:
            return Team.Villagers
        villagers = len(self.survivors(Team.Villagers))
        if villagers <= werewolves:
            return Team.Werewolves
        return None

    @model_validator(mode="after")
    def agent_quantity(self):
        n = len(self.roles)
        if n != len(self.alive) or n != len(self.known_identity):
            raise ValueError(f"Invalid {self}")
        return self

    @classmethod
    def random_roles(cls, n: Annotated[int, Ge(5)] = 5) -> Self:
        if n < 5:
            raise ValueError("At least 5 players are needed to play Werewolf.")
        werewolves = 2 if n <= 15 else n // 4
        roles = (
                [Role.Seer, Role.Doctor]
                + [Role.Werewolf] * werewolves
                + [Role.Villager] * (n - 2 - werewolves)
        )
        shuffle(roles)
        return cls.from_roles(*roles)

    @classmethod
    def from_roles(cls, *roles: Role) -> Self:
        alive = [True] * len(roles)
        known_identity = {i: {i} for i in range(len(roles))}
        werewolves = {
            i for i, werewolf in enumerate(roles) if werewolf is Role.Werewolf
        }
        for werewolf in werewolves:
            known_identity[werewolf] |= werewolves
        return cls(roles=roles, alive=alive, known_identity=known_identity)

    @property
    def seer(self) -> Optional[AgentIndex]:
        return self.singleton_role(Role.Seer)

    @property
    def doctor(self) -> Optional[AgentIndex]:
        return self.singleton_role(Role.Doctor)

    def singleton_role(
            self, role: Union[Role.Seer, Role.Doctor]
    ) -> Optional[AgentIndex]:
        try:
            return next(iter(self.survivors(role)))
        except StopIteration:
            return None

    def active(self) -> set[AgentIndex]:
        if self.phase == Phase.Day:
            return self.survivors()
        return self.survivors(Role.Werewolf, Role.Seer, Role.Doctor)

    def learn_identity(self, knower: AgentIndex, known: AgentIndex) -> None:
        self.known_identity[knower].add(known)

    def observations(self) -> Iterator[tuple[AgentIndex, Observation]]:
        for agent in self.active():
            known_role = {
                known_agent: self.roles[known_agent]
                for known_agent in self.known_identity[agent]
            }
            observation = Observation(
                day=self.day,
                phase=self.phase,
                alive=copy(self.alive),
                known_role=copy(known_role),
                voted=copy(self.voted),
            )
            yield agent, observation

    def survivors(self, *role_filters: Role | Team) -> set[AgentIndex]:
        counted_roles = set()
        for role_filter in role_filters:
            if isinstance(role_filter, Role):
                counted_roles.add(role_filter)
            else:
                counted_roles |= role_filter.roles
        return {
            i
            for i, (role, alive) in enumerate(zip(self.roles, self.alive))
            if alive and (not role_filters or role in counted_roles)
        }

    def kill(self, agent: AgentIndex) -> None:
        self.alive[agent] = False

    def agent_name(self, agent: AgentIndex) -> str:
        return f"{self.roles[agent]}({agent})"

    def __str__(self) -> str:
        s = []
        for agent, (alive, role) in enumerate(zip(self.alive, self.roles)):
            if not alive:
                continue
            known = ", ".join(str(i) for i in sorted(self.known_identity[agent]))
            s.append(f"{agent}. {role} [{known}]")
        return f"{self.phase} {self.day}: " + ", ".join(s)
