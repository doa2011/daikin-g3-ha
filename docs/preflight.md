# G3 只读协议预检（2026-11-23 UTC）

新增 `daikin_g3/preflight.py`：依次执行 `GET /api/v1/info`、`GET /api/v1/status`、`GET /api/v1/capabilities`，由现有 `CommunityAdapter` 完成 Basic 认证、MessagePack 解码与严格能力校验。预检不发送 `POST /api/v1/command`，不触发屏幕或 MCU 写操作，不自动重试，也不降级到旧版 JSON。

使用示例（仅在已经安装**匹配的社区固件**的设备上）：

```python
import asyncio
from daikin_g3.community import CommunityAdapter
from daikin_g3.preflight import probe

async def main():
    adapter = CommunityAdapter("http://192.168.1.100", password=None)
    result = await probe(adapter)
    print("protocol_reachable:", result.protocol_reachable)
    print("supported actions:", sorted(result.actions))
    print("info field names:", result.info_keys)
    print("status field names:", result.status_keys)

asyncio.run(main())
```

若设备设置管理密码，需安全提供密码；不要将密码或设备身份信息写入日志。结果仅包含 info/status 的字段**名称**，不保存其值，以避免泄漏设备 ID 等隐私字段。支持的动作来自设备真实返回的能力集合，不根据型号或固件版本字符串猜测屏幕/媒体能力。若认证失败、编码不匹配或返回无效结构，直接失败，不宣称实机支持。

依据上游 [device-api.md](https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/docs/public/device-api.md) v1.0.0：普通 GET 使用 MessagePack；v0.9.27 为 JSON。上游 [LICENSE](https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/LICENSE) 为 GPL-3.0；本模块独立实现，只调用既有适配器，不复制上游固件源码。

验证分级：单元测试仅为 mock；GitHub Actions 通过表示自动化验证；真实 G3 的认证、状态和屏幕功能仍需独立实机验证。预检结果不能证明原厂固件可直接使用社区 API。
