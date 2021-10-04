# 使用api调用

- 基础例子
```python
from pysimpledlna import SimpleDLNAServer, Device

import sys
server = SimpleDLNAServer(8000)
server.start_server()
device: Device = None
#使用第一台设备进行播放
for i, d in enumerate(server.get_devices(5)):
    device = d
    break
if device is None:
    print('没有找到播放设备')
    sys.exit()
# 服务器根据device key创建资源
server.register_device(device)
# 将文件添加到服务器中，返回一个http协议的地址
file_url = device.add_file(r'E:\video\file.mp4')
# 设置播放文件
device.set_AV_transport_URI(file_url)
# 播放
device.play()
```
- 同步播放器状态

需要在本机获得DLNA播放器状态时可以设置hook
```python
import time
def hook(type, old_value, new_value):
    print(time.time(), ' type:', type, ' old value:', old_value, ' new value:', new_value)
device.set_sync_interval(1)
device.set_sync_hook(hook, hook, None)
device.start_sync_remote_player_status()
```
- 在已知设备地址的情况下，可以直接获得设备对象
```python
device: Device = server.find_device('http://192.168.1.1:1901/')
```
- 服务器启用ssl
```python
server = SimpleDLNAServer(
    server_port=8000,
    is_enable_ssl=True,
    cert_file='cert file path',
    key_file='key file path'
)
```
- 对网络视频进行投屏

将`device.set_AV_transport_URI(file_url)`中的`file_url`设置成其他服务器的地址即可，需要视频文件的真实地址，不支持解析网页获得视频地址
