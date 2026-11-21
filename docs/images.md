# JPEG 预处理
第八轮 CI 44745149168 成功。独立 Pillow 模块：EXIF方向、透明背景合成、contain/cover、RGB baseline JPEG 4:2:0、480×854上限、128KiB上传预算、CRC32。质量逐级降低，超限明确失败。32KiB MJPEG共享缓冲限制不同于上传限制；本模块未实现流式传输。尚未验证 MCU 硬件解码，后续应检查实际 JPEG marker 和实机显示。默认黑底、contain、质量90起为项目实现选择。
