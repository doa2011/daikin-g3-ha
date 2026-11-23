"""Read-only, evidence-based module capability assessment.

No model-based guessing, control requests, or claim of physical validation.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Iterable

from .preflight import PreflightResult


class Support(str, Enum):
    DECLARED = "declared"
    NOT_DECLARED = "not_declared"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class CapabilityAssessment:
    module: str
    support: Support
    required_actions: frozenset[str]
    missing_actions: frozenset[str]
    hardware_verified: bool = False


def assess(
    result: PreflightResult | None,
    requirements: Mapping[str, Iterable[str]],
) -> tuple[CapabilityAssessment, ...]:
    """Assess only caller-declared action requirements.

    None means no successful device preflight; an empty action set after a
    successful preflight is different and yields NOT_DECLARED. A module with
    no declared requirements is UNVERIFIED, not implicitly supported.
    """
    assessments = []
    for module, actions in requirements.items():
        if not isinstance(module, str) or not module:
            raise ValueError("module name must be nonempty")
        required = frozenset(actions)
        if not required or not all(isinstance(a, str) and a for a in required):
            if required:
                raise ValueError("action names must be nonempty strings")
            support = Support.UNVERIFIED
            missing = frozenset()
        elif result is None or not result.protocol_reachable:
            support = Support.UNVERIFIED
            missing = frozenset()
        else:
            missing = required - result.actions
            support = Support.NOT_DECLARED if missing else Support.DECLARED
        assessments.append(CapabilityAssessment(module, support, required, missing))
    return tuple(assessments)
