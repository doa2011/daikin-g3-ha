# G3 接入预检（简化版）

Home Assistant 添加社区固件 G3 时，只做必要检查：

1. 连接 `/api/v1/info`，要求 HTTP 请求成功且响应可解码为 MessagePack map。
2. 要求 `info.model == "daikin"`。
3. 尝试读取 `/api/v1/capabilities`；能力接口失败、暂不可用或列表为空，不阻止添加设备。
4. 不在配置阶段请求 status，不发送任何写入命令。

用户名固定为 `admin`；密码可留空。密码是否正确由设备 HTTP 响应决定，401/403 仍提示认证失败。

不再强制要求 info 包含 firmware_version、protocol、protocol_version、wire_version、default_wire_format 或 wire_formats。这些字段不是接入门槛。MessagePack 格式由底层解码器验证，而不是依赖设备重复声明。

运行时功能根据 capabilities 实际结果启用；未知或未列出的能力不应阻止基础设备接入。
