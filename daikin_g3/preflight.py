"""Read-only preflight for community-firmware G3; never sends control commands.

This module deliberately does not guess firmware baseline from model names.
Only the actual MessagePack endpoints can establish protocol compatibility.
"""
from dataclasses import dataclass
from typing import Protocol, Any


class ReadOnlyAdapter(Protocol):
    async def info(self) -> dict: ...
    async def status(self) -> dict: ...
    async def capabilities(self) -> frozenset[str]: ...


@dataclass(frozen=True)
class PreflightResult:
    protocol_reachable: bool
    actions: frozenset[str]
    info_keys: tuple[str, ...]
    status_keys: tuple[str, ...]


async def probe(adapter: ReadOnlyAdapter) -> PreflightResult:
    """Probe only GET info/status/capabilities; propagate auth/protocol errors.

    Avoid persisting values from info/status: device identifiers and other
    fields may be sensitive. An empty actions set is valid but not proof
    that screen or media features are supported.
    """
    info = await adapter.info()
    if not isinstance(info, dict):
        raise ValueError("expected info and status maps")
    status = await adapter.status()
    if not isinstance(status, dict):
        raise ValueError("expected info and status maps")
    actions = await adapter.capabilities()
    if not isinstance(actions, frozenset) or not all(
        isinstance(action, str) and action for action in actions
    ):
        raise ValueError("expected validated capability action set")
    return PreflightResult(
        protocol_reachable=True,
        actions=actions,
        info_keys=tuple(sorted(k for k in info if isinstance(k, str))),
        status_keys=tuple(sorted(k for k in status if isinstance(k, str))),
    )
