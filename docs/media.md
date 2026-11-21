# 图片上传
第九轮 CI 44745470125 成功。根据上游 BRY88BBA15G/screen_media.inc 与 protocol/media_wire.h，begin/chunk/commit，512字节 Base64，逐命令匹配 request.sequence/id/state/result，最终检查 ready/offset/total/crc32。失败停止，不自动重发或清理不确定操作；用户可明确 cancel。50ms轮询和8秒命令超时为本地策略。当前模拟测试使用合成字节验证传输，不代表 JPEG 硬件解码。跨客户端并发和实际吞吐仍需验证。
