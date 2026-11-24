# G3 屏幕媒体中心：电子相册与摄像头

## 当前实现边界

- start_album / stop_album：从 HA 可访问的本地目录轮播 JPEG/PNG/WebP。群晖 NAS 可先挂载到 HA 可访问路径，再把挂载目录交给服务。
- show_camera：调用 Home Assistant camera.async_get_image 获取单帧 JPEG/截图，再走现有 G3 图片上传与通知协议。当前是截图展示，不是连续视频流。
- show_message、show_dashboard：作为前台媒体任务，会先请求停止后台相册。
- 相册停止是协作式的：当前照片显示终结后才停止，不会对正在执行的 MCU 命令强制取消。
- 相册目录应是 Home Assistant 进程可读的受信任目录；NAS 目录需要先在 HA 主机/容器中挂载。
- 当前相册服务使用目录路径；任意 URL 清单、HA Media Source 浏览选择、远程相册认证尚未实现。

## 启动电子相册

```yaml
action: daikin_g3.start_album
data:
  entry_id: "G3配置条目ID"
  directory: /media/photos
  shuffle: true
  seconds: 30
  brightness: 30
  wake: false
```

停止：

```yaml
action: daikin_g3.stop_album
data:
  entry_id: "G3配置条目ID"
```

## 摄像头截图

```yaml
action: daikin_g3.show_camera
data:
  entry_id: "G3配置条目ID"
  camera: camera.front_door
  seconds: 20
  brightness: 60
  wake: true
```

摄像头实体须已在 HA 中可用。调用成功表示截图已获取并进入 G3 通知/媒体协议流程，不代表屏幕实际显示成功。

## 调度策略

每台 G3 一个后台相册任务。启动第二个相册会拒绝；摄像头、消息通知和仪表盘到来时，先设置相册 stop Event，等待当前照片显示流程结束，再执行前台操作。这样避免两组媒体命令同时争用 MCU。HA 服务的设备级锁继续串行化入口调用。

## 实机验证清单

1. 在社区固件上确认能力集包含 screen.media.get/begin/chunk/commit/cancel 与 screen.push.send。
2. 先单张图片测试：确认屏幕画面、方向、颜色、裁剪和亮度。
3. 使用 3 张以上图片启动相册，确认轮播时长、顺序/随机模式。
4. 轮播期间调用 stop_album，确认当前照片结束后停止。
5. 轮播期间触发 show_camera，确认相册让位且摄像头截图显示；当前策略不自动恢复相册。
6. 测试 NAS 挂载目录、无权限目录、空目录、损坏图片、超大图片。
7. 断网、G3 超时、MCU busy 时检查任务退出与资源保留；不确定状态下不得自动重发或删除仍可能被引用的图片。

## 未完成

- URL 列表与 HA Media Source 相册浏览。
- 摄像头连续视频/MJPEG 流；目前只抓取单帧。
- 前台结束后自动恢复相册、优先级队列和用户可见播放状态传感器。
- G3 实机端到端验证。
