# Decorator pattern in the greenhouse project

Policies wrap the actuator port without callers noticing. Every layer implements `ActuatorPort.apply(device_id,
command, payload)`, so a caller holds one `ActuatorPort` no matter how many wrappers are stacked.

## Wrapping and order

    LoggingActuatorDecorator -> MaxRunTimeActuatorDecorator -> SimulationActuatorAdapter

- `LoggingActuatorDecorator` is outermost. It always writes one `actuator_execution_log` row: success
  (`["logging"]`, no message) or failure (the policy name from the error, then `"logging"`, plus the message).
- `MaxRunTimeActuatorDecorator` raises `PolicyViolationError("maxRunTime", "Max run time exceeded")` when the
  persisted state is `running` and `actuator_states.updated_at` is at least 30 minutes old. It does not call the
  inner adapter, so the simulation never runs for a blocked attempt (proved in `test_max_runtime_does_not_call_inner`).
- `SimulationActuatorAdapter` is the innermost, real adapter.
- The chain is composed in `application/actuators/service.py`, not in the router.

## Why outermost logging

Because logging wraps the policy, a blocked attempt is still recorded, with the policy that blocked it.

## Why Decorator and not inheritance

Inheritance would need a subclass per combination (logging+maxRuntime, logging only, maxRuntime only...). Decorators
compose freely at runtime: add, remove or reorder layers without touching the adapter or the callers.

## Not in this phase

The command string is not validated. An unknown command on an idle actuator succeeds. Phase 10 consults
`allowed_commands`.