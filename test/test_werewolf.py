import pathlib
import sys

import pytest

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "src"))
from werewolf import WerewolfMachine, GameMessage, Command


@pytest.mark.asyncio
async def test_state_machine_completes_cleanly():
    machine = WerewolfMachine()
    await machine.handle_message(GameMessage(command=Command.NEXT))
    await machine.handle_message(GameMessage(command=Command.NEXT))
    await machine.handle_message(GameMessage(command=Command.FINISH))
    assert machine.current_state.final
