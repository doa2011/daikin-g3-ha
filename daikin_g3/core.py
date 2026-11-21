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
        # 取消正在等待设备能力查询的启用操作，避免旧查询结果重新启用模块。
        self._enable_versions = {}
    def register(self, module: Module):
        if module.allowed_actions is not None and not module.allowed_actions <= module.requires:
            raise ValueError('allowed actions must be declared in required capabilities')
        if module.name in self.modules:
            raise ValueError('duplicate module')
        self.modules[module.name] = module
    async def enable(self, name):
        module = self.modules[name]
        version = self._enable_versions.get(name, 0)
        capabilities = await self.adapter.capabilities()
        if version != self._enable_versions.get(name, 0):
            raise RuntimeError('module enable cancelled')
        if not module.requires <= capabilities:
            raise RuntimeError('unsupported capabilities')
        self.enabled.add(name)
    def disable(self, name):
        # 同步禁用不等待 I/O；版本号使进行中的 enable 不会在禁用后重新生效。
        self._enable_versions[name] = self._enable_versions.get(name, 0) + 1
        self.enabled.discard(name)
    async def call(self, name, action, params):
        async with self.lock:
            if name not in self.enabled:
                raise RuntimeError('module disabled')
            # 设备重启、固件变更或能力撤销后，不沿用启用时的旧授权。
            # 在发送任何命令之前重新检查模块所需能力，避免越权控制。
            required = self.modules[name].requires
            capabilities = await self.adapter.capabilities()
            # 能力查询期间可能被同步 disable；必须在实际发送前再次核对。
            if name not in self.enabled:
                raise RuntimeError('module disabled')
            if not required <= capabilities:
                self.enabled.discard(name)
                raise RuntimeError('module capabilities revoked')
            allowed = self.modules[name].allowed_actions
            if allowed is not None and action not in allowed:
                raise RuntimeError('action not allowed for module')
            return await self.adapter.call(action, params)
