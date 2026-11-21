# daikin-g3-ha

面向社区固件大金 G3 的模块化 Python 控制与 Home Assistant 集成实验项目。

## 已有实现

- Basic 管理认证、HTTP MessagePack 命令、请求 ID 和回执校验；仅适用于匹配的社区固件协议，不适用于原厂 G3 直接控制
- 能力发现、模块启停、命令串行化；模块可选 `allowed_actions` 白名单隔离，未配置白名单的旧模块仍按原有行为工作
- 屏幕、诊断、外部数据、图片/媒体、相册、仪表盘、图表、通知等独立 Python 模块与单元测试
- Home Assistant 自定义组件及运行时配置流验证、安装测试包
- OpenWrt 原厂 G3 迁移准备工具与中文说明

## 验证

```sh
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

CI 中的 HA 集成测试使用 Home Assistant 2026.10.1，属于模拟/运行时测试，不代表已经连接真实 G3。请从 Actions 下载 `daikin-g3-ha-test`，而不是直接将本仓库根目录作为 HA 集成目录。

## 限制与安全

当前缺少真实 G3 实机认证、屏幕和媒体端到端测试；原厂固件需先按上游迁移流程操作，不能直接使用社区 API。写操作收到 `accepted` 不代表 MCU 已完成执行；不得在超时后自动重发。固件与脚本必须使用同一上游发布版本。

详见 [协议说明](docs/protocol.md)、[原厂迁移指南](docs/stock-migration-android-windows-openwrt.md) 与 [上游项目](https://github.com/phicomm-io/iotcloud-community-firmware)。
