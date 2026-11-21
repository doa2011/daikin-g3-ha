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

class Core:
    def __init__(self, adapter: Adapter):
        self.adapter = adapter
        self.modules = {}
        self.enabled = set()
        self.lock = asyncio.Lock()
    def register(self, module: Module):
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
            return await self.adapter.call(action, params)
