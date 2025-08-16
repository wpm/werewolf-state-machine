"""
Werewolf – engine-free, interactive skeleton using `python-statemachine`.

- States: Night (initial), Day, Finished (final)
- Events: `next()` (Night ↔ Day), `finish()` (→ Finished)
- No demo producer; the program idles until you type commands.

Setup:
    python -m venv .venv && source .venv/bin/activate
    pip install python-statemachine pydantic
    python werewolf_sm.py
"""

from __future__ import annotations

import asyncio
from enum import StrEnum
from typing import Any

from pydantic import BaseModel
from statemachine import State, StateMachine


# ------------------------------
# Messages
# ------------------------------
class Command(StrEnum):
    NEXT = "next"  # Advance Night<->Day
    FINISH = "finish"  # End the game (-> Finished)
    QUIT = "quit"  # Exit interactive loop (not a state transition)


class GameMessage(BaseModel):
    """Envelope for messages that trigger transitions."""

    command: Command
    data: dict[str, Any] | None = None  # Reserved for future use


# ------------------------------
# The Werewolf State Machine
# ------------------------------
class WerewolfMachine(StateMachine):
    """State machine for game phases only (no player data)."""

    # States
    night = State("Night", initial=True)
    day = State("Day")
    finished_state = State("Finished", final=True)

    # Transitions
    next = night.to(day) | day.to(night)
    finish = night.to(finished_state) | day.to(finished_state)

    # Hooks
    def on_enter_night(self):
        print("🌙 Entered Night. (Werewolves act; villagers sleep.)")

    def on_exit_night(self):
        print("🌅 Exiting Night → transitioning...")

    def on_enter_day(self):
        print("☀️  Entered Day. (Discussion, accusations, and voting.)")

    def on_exit_day(self):
        print("🌘 Exiting Day → transitioning...")

    def on_enter_finished_state(self):
        print("🏁 Game has reached Finished state. No further moves allowed.")

    # Async-friendly dispatcher
    async def handle_message(self, msg: GameMessage) -> None:
        print(
            f"SM: received {msg.command.value!r} while in state {self.current_state.id}."
        )
        if msg.command == Command.NEXT:
            self.next()
        elif msg.command == Command.FINISH:
            self.finish()
        elif msg.command == Command.QUIT:
            pass
        else:
            print(f"SM: unknown command {msg.command!r} (ignored).")


# ------------------------------
# Interactive stdin loop only
# ------------------------------
async def stdin_reader(machine: WerewolfMachine) -> None:
    loop = asyncio.get_running_loop()
    print("\nType commands: `next`, `finish`, `quit`. Ctrl+C to exit.\n")
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
            print("Unknown command. Use: next | finish | quit")

        if machine.current_state.final:
            print("SM: finished; exiting.")
            break


async def main() -> None:
    machine = WerewolfMachine()
    await stdin_reader(machine)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
