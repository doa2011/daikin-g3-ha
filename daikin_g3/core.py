from typing import Protocol, Any
from dataclasses import dataclass
import asyncio

class Adapter(Protocol):
    async def capabilities(self) -> frozenset[str]: ...
    async def call(self, action: str, params: dict) -> Any: ...

@dataclass(frozen=True)
class Module:
    name: str
    requires: frozenset[str] = frozenset()
    allowed_actions: frozenset[str] | None = None

class Core:
    def __init__(self, adapter: Adapter):
        self.adapter = adapter
        self.modules = {}
        self.enabled = set()
        self.lock = asyncio.Lock()
    def register(self, module: Module):
        if module.allowed_actions is not None and not module.allowed_actions <= module.requires:
            raise ValueError('allowed actions must be declared in required capabilities')
        if module.name in self.modules:
            raise ValueError('duplicate module')
        self.modules[module.name] = module
    async def enable(self, name):
        module = self.modules[name]
        if not module.requires <= await self.adapter.capabilities():
            raise RuntimeError('unsupported capabilities')
        self.enabled.add(name)
    def disable(self, name):
        self.enabled.discard(name)
    async def call(self, name, action, params):
        async with self.lock:
            if name not in self.enabled:
                raise RuntimeError('module disabled')
            # 设备重启、固件变更或能力撤销后，不沿用启用时的旧授权。
            # 在发送任何命令之前重新检查模块所需能力，避免越权控制。
            required = self.modules[name].requires
            if not required <= await self.adapter.capabilities():
                self.enabled.discard(name)
                raise RuntimeError('module capabilities revoked')
            allowed = self.modules[name].allowed_actions
            if allowed is not None and action not in allowed:
                raise RuntimeError('action not allowed for module')
            return await self.adapter.call(action, params)
