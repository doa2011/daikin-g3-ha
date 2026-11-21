# 外部组件数据
第六轮 CI 44744868217 attempt 1：实际日志 26 tests OK，无 artifacts。依据上游 BRY88BBA15G/screen_commands.inc 的 screen.data.push：id 1..65535，TTL 1..86400 秒，数值最多64个，有限且绝对值不超过1e9，文本最多192 UTF-8字节。组件必须预先配置 external binding；固件负责最终检查。ok 仅表示桥接发送成功，并非显示确认。数据易失，不写布局。新增独立 ExternalData 类及边界测试；未实现 HA 实体订阅、历史曲线或实机验证，缺测不自动填零。下一轮验证 series 的图表参数。
