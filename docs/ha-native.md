# HA 原生集成实验
第十五轮：新增原生实体及摄像头读取器、Config Flow、配置入口生命周期和打包脚本。运行 `python scripts/package_ha.py dist` 后复制 dist/custom_components/daikin_g3 到 HA 配置目录。源码目录本身不含核心副本，不可直接复制。前轮 CI 44750481040 已通过60项测试。本轮仅打包与语法测试，尚无真实 HA 环境验证、服务注册、实体平台或实机验证。不要作为生产版本部署。
