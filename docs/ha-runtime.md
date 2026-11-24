# 第十八轮：真实 HA 运行库与测试包
2026-11-20：前轮 44751587023 attempt 1 已通知，67 项测试通过，无 artifacts。新增独立 HA 2026.10.1 CI，验证服务注册、选择器构造、服务调用和卸载；G3 传输仍为模拟，非硬件测试，也未覆盖完整 Config Flow。通过后上传可安装 ZIP。原厂设备仍须按上游迁移指南核对硬件及恢复路径，不混入设备固件。首次运行可能暴露 HA API 或依赖兼容性问题，按日志修复。

## 第十九轮：运行环境修复
2026-11-20：57d8279 的 Unit tests run 44763382458 attempt 1 成功；HA integration run 44763382529 attempt 1 失败，job 136381497936。两者无 artifacts。本轮汇报上述终态。首个根因为 HA 2026.10.1 要求 Python >=3.14.2，而工作流使用 3.13，pip 安装阶段退出。仅将 HA 工作流固定为 3.14.2，保留既有 HA 版本和所有测试，不降低验证要求。待新 CI，尚无实机验证。

## 第二十轮：Runner 与 Python 构建兼容性
2026-11-20：97e96b2 的 Unit tests 44773028933 attempt 1 成功，67 项测试；HA integration 44773029087 attempt 1 失败，job 136415375771，首个根因 Ubuntu 26.04 无 Python 3.14.2 x64 构建。两者无 artifacts，本轮汇报终态。核对 actions/python-versions 官方 versions-manifest.json，稳定版 3.14.10 提供 Ubuntu 24.04 和 26.04 x64 构建，固定 ubuntu-24.04 与 3.14.10，满足 HA 最低版本要求。保留所有验证及打包步骤，未执行真实 HA 测试。

## 第二十一轮：HA ConfigEntry 构造兼容性
2026-11-20：affbbed 的 Unit tests 44782559032 attempt 1 成功，67 项；HA integration 44782560898 attempt 1 失败，job 136448797186。两者无 artifacts，本轮汇报终态。Python 与 HA 依赖安装及打包准备已通过，首次进入实际 HA 验证脚本，ConfigEntry 构造缺少必需的 subentries_data 参数。补齐空子入口列表，不跳过验证，不修改生产集成逻辑。待新 CI。

## 第二十二轮：摄像头运行库依赖
2026-11-20：6cadddd 的 Unit tests 44792320181 attempt 1 成功，67 项；HA integration 44792320303 attempt 1 失败，job 136482914330。两者无 artifacts，本轮汇报终态。ConfigEntry 已通过构造，失败发生于 native_bridge 导入 camera -> stream -> numpy。核对 HA 2026.10.1 camera/stream manifest，依赖包含 PyTurboJPEG 1.8.3、av 19.0.0、numpy 2.3.2。独立测试脚本未执行 HA 的集成依赖加载，故在 CI 中读取已安装 HA manifest 并安装声明依赖，另安装 libturbojpeg0；不修改生产集成、不模拟 camera 模块、不跳过验证。待 CI，尚无实机验证。

## 第二十三轮：Ubuntu JPEG 系统库包名
2026-11-20：34f1853 的 Unit tests 44801560502 attempt 1 成功（67项，0.565秒）；HA integration 44801561084 attempt 1 失败，job 136514730240，均无 artifacts。本轮汇报终态。首个根因 apt 无法定位 libturbojpeg0，Ubuntu Noble 使用 libturbojpeg 包名；改为该包并显式检查动态链接库存在。保留真实 HA 验证与打包流程，待 CI。

## 第二十四轮：首次 HA 集成构建成功及双设备生命周期回归
2026-11-20：95a57db 的 Unit tests run 44811612359 attempt 1 成功，67/67；HA integration run 44811611461 attempt 1 成功，job 136549329903，artifact 14667695557 (daikin-g3-ha-test，16454 bytes)。两项均已核实，本轮首次通知上述结果。实际 HA 2026.10.1 服务注册、选择器、调用和卸载测试通过，仍使用模拟 G3 传输，不代表实机成功。新增第二个 ConfigEntry 组合验证：两个设备同时加载、卸载第一个后共享服务保持注册、第二个仍可调用、最后一个卸载后服务移除。继续通过真实 HA CI 检查，不修改设备固件。

## 第二十五轮：Config Flow 真实 HA 运行库验证
2026-11-21：恢复提交 ddf1253 的 Unit tests run 44863386231 attempt 1 与 HA integration run 44863386243 attempt 1 均成功；HA artifact 14690004992 已核实。完整源码树已恢复。新增对真实 HA ConfigFlow 类的集成回归测试：有效 URL 的设备信息/能力检查及规范化、非法地址表单错误、设备离线表单错误。设备适配器仍采用模拟，不连接真实 G3；测试不涉及刷机。提交后须等待新的 CI 结果，不将新增测试标记为已通过。

## 接入故障修复（2026-11-24）
实机反馈无法连接，根因尚未确认。a8a557a 的 45459525117、45459525180 attempt 1 均成功（126 项单测，HA artifact 14951702846），本轮已通知。776f834 接受裸 IP/端口并校验端口，d9bdda4 增加真实适配器构造断言；尚待 CI，未改变认证或写命令重试策略。
