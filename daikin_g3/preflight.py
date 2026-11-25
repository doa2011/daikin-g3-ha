"""Read-only identity and authentication preflight for community G3."""
from dataclasses import dataclass
from typing import Protocol


class ReadOnlyAdapter(Protocol):
    async def info(self) -> dict: ...
    async def status(self) -> dict: ...
    async def capabilities(self) -> frozenset[str]: ...


@dataclass(frozen=True)
class PreflightResult:
    # Keep the original four positional fields stable for existing consumers.
    protocol_reachable: bool
    actions: frozenset[str]
    info_keys: tuple[str, ...]
    status_keys: tuple[str, ...]
    model: str = ""
    firmware_version: str = ""


def validate_g3_identity(info: dict) -> tuple[str, str]:
    """Require the documented v1.0.0 Daikin community wire identity."""
    if not isinstance(info, dict):
        raise ValueError("invalid info map")
    model = info.get("model")
    version = info.get("firmware_version") or info.get("version")
    if model != "daikin":
        raise ValueError("unsupported device model")
    if not isinstance(version, str) or not version.strip():
        raise ValueError("missing firmware version")
    if info.get("protocol") != "tmcp":
        raise ValueError("unsupported command protocol")
    if info.get("protocol_version") != 2 or info.get("wire_version") != 1:
        raise ValueError("unsupported wire protocol version")
    if info.get("default_wire_format") != "msgpack":
        raise ValueError("unsupported wire format")
    formats = info.get("wire_formats")
    if not isinstance(formats, list) or "msgpack" not in formats:
        raise ValueError("MessagePack is not declared by device")
    return model, version


async def probe(adapter: ReadOnlyAdapter) -> PreflightResult:
    """Authenticate and verify identity using read-only GET endpoints only."""
    info = await adapter.info()
    model, version = validate_g3_identity(info)
    status = await adapter.status()
    if not isinstance(status, dict):
        raise ValueError("invalid status map")
    actions = await adapter.capabilities()
    if not isinstance(actions, frozenset) or not all(
        isinstance(action, str) and action for action in actions
    ):
        raise ValueError("invalid capability action set")
    return PreflightResult(
        protocol_reachable=True,
        actions=actions,
        info_keys=tuple(sorted(k for k in info if isinstance(k, str))),
        status_keys=tuple(sorted(k for k in status if isinstance(k, str))),
        model=model,
        firmware_version=version,
    )
