# daikin-g3-ha
第一阶段实验骨架：适配器接口、模块注册、能力检查、串行命令调度、独立启停。
运行测试：`python -m unittest discover -s tests -v`。
目前仅模拟适配器测试，尚未实现实际认证、MessagePack、HA 集成或屏幕操作。
后续模块：display、diagnostics、air_sensor、external_sensor、image_processor、media、photo_album、dashboard、charts、camera、notification、weather_clock、firmware。ESPHome、BLE Proxy、HomeKit 后续单独评估。模块依赖与资源抢占尚待实现。
参考上游：https://github.com/phicomm-io/iotcloud-community-firmware
