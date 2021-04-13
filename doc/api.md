# 使用api调用

## 完整例子
```python
from pysimpledlna import SimpleDLNAServer, Device
import time
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
# 将文件添加到服务器中，返回一个http协议的地址
file_url = device.add_file(r'E:\video\file.mp4')
# 设置播放文件
device.set_AV_transport_URI(file_url)
# 播放
device.play()
# 同步播放器和服务器状态
def hook(type, old_value, new_value):
    print(time.time(), ' type:', type, ' old value:', old_value, ' new value:', new_value)
device.set_sync_interval(1)
device.set_sync_hook(hook, hook, None)
device.start_sync_remote_player_status()
```

在已知设备地址的情况下，可以直接获得设备对象
```python
device: Device = server.find_device('http://192.168.1.1:1901/')
```

