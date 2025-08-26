from __future__ import annotations

import asyncio
from collections import Counter

from statemachine import AsyncStateMachine, State
from statemachine.dispatcher import Event

from . import (
    Werewolf,
    Phase,
    Observation,
    Action,
    Role,
    AgentIndex,
)


class WerewolfMachine(AsyncStateMachine):
    """Asynchronous state machine implementing Werewolf game flow.

    The machine acts as a reinforcement learning environment. For each state it
    emits :class:`Observation` objects to agents through the ``observe`` event and
    waits for agents to reply with :class:`Action` objects through the ``action``
    event.
    """

    start = State(Phase.Start, initial=True)
    night = State(Phase.Night)
    day = State(Phase.Day)
    end = State(Phase.End, final=True)

    next = start.to(night) | night.to(day) | day.to(night)
    finish = night.to(end) | day.to(end)

    def __init__(self, game: Werewolf):
        self.game = game
        # Events used to communicate with agents.
        self.observe: Event = Event("observe")
        self.action: Event = Event("action")
        self._actions: asyncio.Queue[Action] = asyncio.Queue()
        # enqueue actions from agents
        self.action += self._queue_action
        super().__init__()

    async def _queue_action(self, action: Action) -> None:
        """Store actions triggered by agents."""
        await self._actions.put(action)

    async def dispatch(self, agent: AgentIndex, observation: Observation) -> Action:
        """Send ``observation`` to ``agent`` and wait for its ``Action``."""
        await self.observe.trigger(agent=agent, observation=observation)
        while True:
            action = await self._actions.get()
            if action.selector == agent:
                return action
            # not this agent's action yet; put back and wait
            await self._actions.put(action)

    async def on_enter_night(self) -> None:
        self.game.phase = Phase.Night
        await self._phase_night()

    async def on_enter_day(self) -> None:
        self.game.phase = Phase.Day
        await self._phase_day()

    async def _phase_night(self) -> None:
        pending_kill: AgentIndex | None = None
        protected: AgentIndex | None = None
        votes: dict[AgentIndex, AgentIndex | None] = {}
        for agent, obs in self.game.observations():
            action = await self.dispatch(agent, obs)
            votes[action.selector] = action.selected
            role = self.game.roles[action.selector]
            if role is Role.Werewolf:
                pending_kill = action.selected
            elif role is Role.Seer:
                self.game.learn_identity(action.selector, action.selected)
            elif role is Role.Doctor:
                protected = action.selected
        self.game.voted.append(votes)
        if pending_kill is not None and pending_kill != protected:
            self.game.kill(pending_kill)
        if self.game.winner is not None:
            await self.finish()
        else:
            await self.next()

    async def _phase_day(self) -> None:
        votes: dict[AgentIndex, AgentIndex | None] = {}
        for agent, obs in self.game.observations():
            action = await self.dispatch(agent, obs)
            votes[action.selector] = action.selected
        self.game.voted.append(votes)
        if votes:
            counts = Counter(votes.values())
            victim, _ = counts.most_common(1)[0]
            if victim is not None:
                self.game.kill(victim)
        self.game.day += 1
        if self.game.winner is not None:
            await self.finish()
        else:
            await self.next()
