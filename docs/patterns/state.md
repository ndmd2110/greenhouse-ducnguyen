# State pattern in the greenhouse project

Each actuator has a persisted lifecycle state. The domain owns every transition rule; the API only exposes the
current `state` and the `allowed_commands` derived from it.

## States and legal edges

| From | Allowed targets | Commands allowed in this state |
|---|---|---|
| `off` | `idle`, `error` | none |
| `idle` | `running`, `off`, `maintenance`, `error` | `start_pump` |
| `running` | `idle`, `error` | `stop_pump` |
| `error` | `idle` (reset), `maintenance` | none |
| `maintenance` | `idle`, `error` | none |

Every edge not in the table is illegal, including a transition to the current state. `* -> error` is allowed from
every state except `error` itself. `running -> maintenance` is deliberately illegal: stop the actuator first.

## Where things live

- `domain/actuators/state.py` – the transition table; one `StateSpec` per state holds its next states and commands.
- `domain/actuators/context.py` – `ActuatorContext.transition(target)` validates, then mutates. It raises
  `IllegalTransitionError` (or `UnknownStateError`) *before* changing anything.
- `application/devices/state_service.py` – load -> transition -> save. If the context raises, `save` is never reached,
  so the stored row stays untouched.
- `infrastructure/persistence/actuator_state_repository.py` – the `actuator_states` table, keyed by `device_id`.
- The React UI only displays `state` / `allowed_commands`; it never decides what is legal.

## Persistence and seeding

State lives in `actuator_states`, not in process memory, so a backend restart keeps it. Existing actuators are
seeded to `idle` inside the migration `c1a9f0e27d35`'s `upgrade()`. New actuators get their row in
`DeviceRepository.save_device`. Any actuator that still has no row (e.g. SQLite database that was created before the
table existed) resolves to `idle` and gets its row on first read.

## HTTP mapping

`POST /api/devices/{id}/transition {"target": "..."}`: 404 missing actuator (or a sensor), 409 illegal edge, 400
unknown state name. Phase 10 (Command) will check `allowed_commands` before executing.

## Why State and not if/else

Adding a state or edge is a table edit in one file. Routers and React contain no `if state == ...` rules.