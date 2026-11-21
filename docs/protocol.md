# 第二阶段：HTTP / MessagePack
依据上游 docs/public/device-api.md v1.0.0 文档：
https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/docs/public/device-api.md
独立认证、编码和 HTTP 适配器。Basic admin，可信局域网使用，禁用代理与重定向，不自动重发写命令。accepted 不等于实际执行完成。能力 actions 暂按字符串数组严格解析，待核对 G3 源码及实机返回；未实现 JSON 旧版、异步回执跟踪或 HA 接入。本轮测试仅协议及认证，下一轮补充 HTTP mock 与实际能力结构验证。

## 能力结构兼容性校正（2026-11-21）

核对上游 `docs/public/device-api.md`：HTTP `GET /api/v1/capabilities` 是普通数据对象，`capabilities.get` 命令的返回则在 `data.actions` 中。社区适配器现在严格识别顶层 `actions` 和命令式 `data.actions` 两种结构，拒绝非字符串及空动作名，避免错误识别为不支持全部模块。新增独立模拟测试，覆盖两种结构及无效动作。此变更只涉及能力解析，不发送写命令，也未经过实机验证。上游协议代码遵循其仓库许可；本项目未复制固件源码。
