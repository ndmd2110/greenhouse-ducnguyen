class UnknownStateError(ValueError):
    """Target is not one of the known states (API maps this to 400)."""


class IllegalTransitionError(ValueError):
    """The edge is not in the transition table (API maps this to 409)."""


class PolicyViolationError(Exception):
    """A decorator refused to apply a command. Carries the policy name for the execution log."""

    def __init__(self, policy: str, message: str) -> None:
        super().__init__(message)
        self.policy = policy
        self.message = message