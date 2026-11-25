"""Minimal read-only preflight for a reachable MessagePack device."""
import logging
from dataclasses import dataclass
from typing import Protocol

_LOGGER = logging.getLogger(__name__)


class ReadOnlyAdapter(Protocol):
    async def info(self) -> dict: ...
    async def capabilities(self) -> frozenset[str]: ...


@dataclass(frozen=True)
class PreflightResult:
    # Preserve the original positional fields for existing consumers.
    protocol_reachable: bool
    actions: frozenset[str]
    info_keys: tuple[str, ...]
    status_keys: tuple[str, ...]
    model: str = ""
    firmware_version: str = ""


def validate_g3_identity(info: dict) -> tuple[str, str]:
    """Accept any MessagePack map; device model and firmware are informational."""
    if not isinstance(info, dict):
        raise ValueError("invalid info map")
    model = info.get("model")
    version = info.get("firmware_version") or info.get("version")
    return (
        model if isinstance(model, str) else "",
        version if isinstance(version, str) else "",
    )


async def probe(adapter: ReadOnlyAdapter) -> PreflightResult:
    """A successful MessagePack info response is sufficient for onboarding."""
    info = await adapter.info()
    model, version = validate_g3_identity(info)

    # Capability discovery is optional and must never block onboarding.
    try:
        actions = await adapter.capabilities()
        if not isinstance(actions, frozenset) or not all(
            isinstance(action, str) and action for action in actions
        ):
            raise ValueError("invalid capability action set")
    except Exception as exc:
        _LOGGER.debug("Device capability discovery skipped (%s)", type(exc).__name__)
        actions = frozenset()

    return PreflightResult(
        protocol_reachable=True,
        actions=actions,
        info_keys=tuple(sorted(k for k in info if isinstance(k, str))),
        status_keys=(),
        model=model,
        firmware_version=version,
    )
