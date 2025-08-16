"""
Werewolf

- States: Night (initial), Day, Finished (final)
- Events: `next()` (Night ↔ Day), `finish()` (→ Finished)
"""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from statemachine import State, StateMachine

from state import WerewolfState
import typer


class Command(StrEnum):
    NEXT = "next"  # Advance Night<->Day
    FINISH = "finish"  # End the game (-> Finished)
    QUIT = "quit"  # Exit interactive loop (not a state transition)


class GameMessage(BaseModel):
    """Envelope for messages that trigger transitions."""

    command: Command
    data: dict[str, Any] | None = None  # Reserved for future use


class WerewolfMachine(StateMachine):
    """State machine for game phases only (no player data)."""

    # States
    night = State("Night", initial=True)
    day = State("Day")
    finished_state = State("Finished", final=True)

    # Transitions
    next = night.to(day) | day.to(night)
    finish = night.to(finished_state) | day.to(finished_state)

    def __init__(self, state: WerewolfState | None = None) -> None:
        super().__init__(model=state)

    # Hooks
    def on_enter_night(self):
        print("🌙 Entered Night. (Werewolves act; villagers sleep.)")

    def on_exit_night(self):
        print("🌅 Exiting Night → transitioning...")

    def on_enter_day(self):
        print("☀️ Entered Day. (Discussion, accusations, and voting.)")

    def on_exit_day(self):
        print("🌘 Exiting Day → transitioning...")

    def on_enter_finished_state(self):
        print("🏁 Game has reached Finished state. No further moves allowed.")

    async def handle_message(self, msg: GameMessage) -> None:
        print(
            f"SM: received {msg.command.value!r} while in state {self.current_state.id}."
        )
        match msg.command:
            case Command.NEXT:
                self.next()
            case Command.FINISH:
                self.finish()
            case Command.QUIT:
                pass
            case _:
                print(f"SM: unknown command {msg.command!r} (ignored).")


async def stdin_reader(machine: WerewolfMachine) -> None:
    """Command line interface for the Werewolf game.

    Accepts the following commands (shortcuts in parentheses):

    - ``next`` (``n``) – advance Night ↔ Day
    - ``finish`` (``f``) – end the game
    - ``quit`` (``q``) – exit the loop without a transition

    :param machine: Werewolf state machine
    """
    loop = asyncio.get_running_loop()
    print(
        "\nType commands: `next` (n), `finish` (f), `quit` (q). Ctrl+C to exit.\n"
    )
    print("Initial state:", machine.current_state.id)

    while True:
        try:
            line = await loop.run_in_executor(None, input, ">> ")
        except (EOFError, KeyboardInterrupt):
            line = "quit"

        cmd = line.strip().lower()
        if cmd in {Command.NEXT.value, "n"}:
            await machine.handle_message(GameMessage(command=Command.NEXT))
        elif cmd in {Command.FINISH.value, "f"}:
            await machine.handle_message(GameMessage(command=Command.FINISH))
        elif cmd in {Command.QUIT.value, "q"}:
            await machine.handle_message(GameMessage(command=Command.QUIT))
            break
        else:
            print("Unknown command. Use: next|n | finish|f | quit|q")

        if machine.current_state.final:
            print("SM: finished; exiting.")
            break


async def _async_main() -> None:
    state = WerewolfState(roles={})
    machine = WerewolfMachine(state)
    await stdin_reader(machine)


app = typer.Typer()


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:  # pragma: no cover - CLI entry point
    """Run the interactive Werewolf game."""
    if ctx.invoked_subcommand is None:
        try:
            asyncio.run(_async_main())
        except KeyboardInterrupt:
            pass
