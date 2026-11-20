# 第二阶段：HTTP / MessagePack
依据上游 docs/public/device-api.md v1.0.0 文档：
https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/docs/public/device-api.md
独立认证、编码和 HTTP 适配器。Basic admin，可信局域网使用，禁用代理与重定向，不自动重发写命令。accepted 不等于实际执行完成。能力 actions 暂按字符串数组严格解析，待核对 G3 源码及实机返回；未实现 JSON 旧版、异步回执跟踪或 HA 接入。本轮测试仅协议及认证，下一轮补充 HTTP mock 与实际能力结构验证。
