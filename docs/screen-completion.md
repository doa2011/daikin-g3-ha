# MCU 换页回执
第四轮 CI 44732677372 成功。核对 https://github.com/phicomm-io/iotcloud-community-firmware/blob/main/BRY88BBA15G/screen_page.inc ：accepted.data.request 为 uint32，get.data.request 匹配，state 为 pending/complete/invalid_page/mcu_busy/timeout。可用性窗口5秒。新增 confirm=True 等待回执（默认保留旧 accepted 行为）；7秒客户端超时，250ms轮询，不重发写命令；同一 Screen 实例串行化。实机尚未验证，跨客户端请求冲突仅能尽力检测，超时不代表未执行。诊断模块下一轮独立开发。
