# 第十八轮：真实 HA 运行库与测试包
2026-11-20：前轮 44751587023 attempt 1 已通知，67 项测试通过，无 artifacts。新增独立 HA 2026.10.1 CI，验证服务注册、选择器构造、服务调用和卸载；G3 传输仍为模拟，非硬件测试，也未覆盖完整 Config Flow。通过后上传可安装 ZIP。原厂设备仍须按上游迁移指南核对硬件及恢复路径，不混入设备固件。首次运行可能暴露 HA API 或依赖兼容性问题，按日志修复。

## 第十九轮：运行环境修复
2026-11-20：57d8279 的 Unit tests run 44763382458 attempt 1 成功；HA integration run 44763382529 attempt 1 失败，job 136381497936。两者无 artifacts。本轮汇报上述终态。首个根因为 HA 2026.10.1 要求 Python >=3.14.2，而工作流使用 3.13，pip 安装阶段退出。仅将 HA 工作流固定为 3.14.2，保留既有 HA 版本和所有测试，不降低验证要求。待新 CI，尚无实机验证。

## 第二十轮：Runner 与 Python 构建兼容性
2026-11-20：97e96b2 的 Unit tests 44773028933 attempt 1 成功，67 项测试；HA integration 44773029087 attempt 1 失败，job 136415375771，首个根因 Ubuntu 26.04 无 Python 3.14.2 x64 构建。两者无 artifacts，本轮汇报终态。核对 actions/python-versions 官方 versions-manifest.json，稳定版 3.14.10 提供 Ubuntu 24.04 和 26.04 x64 构建，固定 ubuntu-24.04 与 3.14.10，满足 HA 最低版本要求。保留所有验证及打包步骤，未执行真实 HA 测试。

## 第二十一轮：HA ConfigEntry 构造兼容性
2026-11-20：affbbed 的 Unit tests 44782559032 attempt 1 成功，67 项；HA integration 44782560898 attempt 1 失败，job 136448797186。两者无 artifacts，本轮汇报终态。Python 与 HA 依赖安装及打包准备已通过，首次进入实际 HA 验证脚本，ConfigEntry 构造缺少必需的 subentries_data 参数。补齐空子入口列表，不跳过验证，不修改生产集成逻辑。待新 CI。
