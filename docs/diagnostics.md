# 屏幕诊断
第五轮 CI 44744432353 成功。依据上游 BRY88BBA15G/screen_diagnostics.inc 实现独立诊断类，start/stop/read，匹配 request 与 reply_request、超时、每批8条最多96条，检查 generation 和索引。status=0 成功的语义仍需 MCU 端交叉核实；采集期间数据变化则拒绝混合快照，建议采集结束后读取。尚无实机验证。
