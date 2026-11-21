# 原厂 G3 免拆迁移：Android + Windows 10 + OpenWrt（准备阶段）

**状态：网络准备脚本已实现；Android APK、Windows 服务封装、原厂设备 OTA 尚未实现或实机验证。** 此文档不代表可以直接刷机。

上游来源：[phicomm-io/iotcloud-community-firmware/tools/daikin_g3_migrate](https://github.com/phicomm-io/iotcloud-community-firmware/tree/main/tools/daikin_g3_migrate)，GPL-3.0。必须使用同一发布的迁移包、ESP32 raw 应用、屏幕 MCU 镜像和 SHA256SUMS；设备仅限 BRY88BBA15G / SENSOR3_ESP32。

## 已核实的上游通信边界

原厂 BLE 服务 FFFF、写 FF01、通知 FF02。先发送 BLUFi 版本请求 0x1c，收到 0x41 后使用自定义配置 0x4d；配置负载包含 2.4GHz SSID、密码、网关 IPv4 和虚拟网关 MAC（例如 020000000001），超过 16 字节时分片。现有 Linux/macOS 工具可作 Android Kotlin 移植的协议参考，**并非通用 ESP32 BLUFi App 即可完成**。

上游迁移还要求局域网 TCP 443/8883、MQTT、HTTPS、网关应答器和三个 DNS 名称。手机负责 BLE，Windows 10 主机负责服务，OpenWrt 负责 DNS；没有实体网关和 Linux 蓝牙适配器也可规划此架构，但尚待实机联调。

## OpenWrt DNS 规则生成（不自动修改路由器）

Windows 电脑应有固定 DHCP 租约，假设为 192.168.1.10。在本仓库执行：

```sh
python scripts/g3_openwrt_dns.py --host 192.168.1.10
python -m unittest tests.test_g3_openwrt_dns -v
```

生成 dnsmasq `address=/域名/IP` 规则，可用于 OpenWrt dnsmasq 自定义配置。**注意：dnsmasq 地址覆盖规则对使用该解析器的其他客户端也可能生效；必须将 G3 的 DHCP DNS 指向 OpenWrt，且仅在迁移窗口启用这些覆盖，迁移后立即撤销。** 不应声称普通 dnsmasq address 规则能够按客户端隔离；若要求严格单设备 DNS 隔离，应使用单独的 DNS 实例或客户端专属 DNS 服务器。

## Windows 服务与刷机前检查

先按上游 README 用完整迁移包创建服务，确认 Windows 10 支持 Docker Desktop/WSL2、容器端口映射可从 G3 访问、Windows 防火墙放行所需 TCP 443/8883、OpenWrt DNS 解析生效。必须确认设备 Wi-Fi STA MAC（不是 BLE MAC）、网关应答、HTTPS 请求日志，以及发布文件 SHA256SUMS。初始服务器应保持 **no update**；未经确认不得自动执行 enable.py/trigger.py。

上游要求等待 snapshot_upload、get_weather、login_ipbox、get_filter_sensor3、get_error_sensor3 应答，特定原厂屏幕版本需临时 --weather-code 1。只有以上全部通过，才人工确认并发送**一次** ESP32-only OTA 指令。不得把 all.bin、signed 镜像、G1/G2 镜像或屏幕 MCU 镜像用于 ESP32 raw OTA。OTA 完成后再经社区 WebUI 安装配套屏幕固件；最后撤销 DNS、停止临时服务。

## 研发边界

本轮仅增加纯 Python DNS 规则生成与独立测试，**没有 APK、没有实际刷写、没有修改 OpenWrt**。后续独立 Android 工程实现 BLE 扫描/配网及日志导出，Windows 服务封装必须先有只读检查模式。真实 G3 仍是原厂固件，Home Assistant 模拟 CI 成功不能证明原厂迁移成功。
