"""Minimal read-only preflight for a Daikin G3 community-firmware device."""
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
    """Only require a MessagePack map identifying the expected G3 model."""
    if not isinstance(info, dict):
        raise ValueError("invalid info map")
    model = info.get("model")
    if model != "daikin":
        raise ValueError("unsupported device model")
    version = info.get("firmware_version") or info.get("version") or ""
    if not isinstance(version, str):
        version = ""
    return model, version


async def probe(adapter: ReadOnlyAdapter) -> PreflightResult:
    """Authenticate by successfully reading info; capabilities are optional."""
    info = await adapter.info()
    model, version = validate_g3_identity(info)

    # Capability discovery must not block adding a reachable G3. Firmware
    # variants can expose different lists or temporarily report busy.
    try:
        actions = await adapter.capabilities()
        if not isinstance(actions, frozenset) or not all(
            isinstance(action, str) and action for action in actions
        ):
            raise ValueError("invalid capability action set")
    except Exception as exc:
        _LOGGER.debug("G3 capability discovery skipped (%s)", type(exc).__name__)
        actions = frozenset()

    return PreflightResult(
        protocol_reachable=True,
        actions=actions,
        info_keys=tuple(sorted(k for k in info if isinstance(k, str))),
        status_keys=(),
        model=model,
        firmware_version=version,
    )
