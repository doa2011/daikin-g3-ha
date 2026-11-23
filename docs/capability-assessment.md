# G3 能力声明与实机验证分级（2026-11-23）

`daikin_g3/capability_assessment.py` 只消费 `preflight.probe()` 的只读结果；不请求设备、不发控制命令、不依据型号猜测动作。调用方必须从上游协议及目标固件明确所需 action，不能将示例动作当作所有 G3 固件的通用能力。

- `declared`：成功预检的实际 `capabilities` 包含全部所需动作，仅证明设备声明。
- `not_declared`：成功预检但缺少至少一项动作；缺失项列在 `missing_actions`。
- `unverified`：尚未成功预检，或该模块未提供任何动作要求；不能推断支持或不支持。
- `hardware_verified` 固定为 `False`：真实屏幕、MCU、媒体链路必须另行实测，不能用 CI 替代。

```python
from daikin_g3.capability_assessment import assess
# result = await probe(adapter)  # 仅匹配的社区固件
checks = assess(result, {"screen_read": {"screen.page.get"}})
for item in checks:
    print(item.module, item.support.value, sorted(item.missing_actions), item.hardware_verified)
```

以上 `screen.page.get` 仅为示例，实际应以当前固件的 `GET /api/v1/capabilities` 为准。参考 [上游设备 API](https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/docs/public/device-api.md)（v1.0.0 MessagePack，v0.9.27 JSON），上游源码为 GPL-3.0；本模块为独立实现，未复制上游固件源码。

验证等级：本地/CI 单元测试为模拟，HA 集成 CI 为软件集成，实机认证与屏幕操作仍未验证。
