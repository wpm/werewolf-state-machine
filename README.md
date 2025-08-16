# Werewolf State Machine

This implements the following state machine to model game flow in the social
deception game Werewolf.

```mermaid
stateDiagram-v2
    Night --> Day: Next
    Day --> Night: Next
    Night --> [*]: Finished
    Day --> [*]: Finished
```

Players take action by sending `GameMessage` objects to `WerewolfMachine` as appropriate.
