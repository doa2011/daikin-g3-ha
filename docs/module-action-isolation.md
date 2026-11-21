# 模块动作白名单（2026-11-21）

在原有 `Core` 模块注册机制中增加可选 `allowed_actions`，防止已启用的低权限模块通过共享适配器调用无关的控制、复位或升级动作。

```python
from daikin_g3.core import Core, Module
core.register(Module(
    'screen_reader',
    requires=frozenset({'screen.page.get'}),
    allowed_actions=frozenset({'screen.page.get'}),
))
```

白名单必须为声明的 `requires` 子集；注册时检查，调用时再次检查，拒绝的动作不会传给适配器。未配置白名单的历史模块保持兼容行为，后续应逐个迁移到最小权限声明。此检查只限制经 `Core.call` 的调用；直接持有底层适配器的模块仍需单独约束。

依据上游 [设备协议](https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/docs/public/device-api.md)：HTTP 命令采用 MessagePack，`accepted` 仅表示受理。此次属于本地模拟测试和 CI 验证，尚无实机证明。
