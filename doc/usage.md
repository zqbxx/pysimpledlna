使用说明
------
:one: 查找DLNA设备
```
> pysimpledlna list
[ 1 ] Kodi (DESKTOP-O7IVEPH) @ http://192.168.199.151:1901/
```

:two: 播放视频
```
> pysimpledlna play -i test.mkv -u http://192.168.199.151:1901/
```

:three: 播放列表
大多数dlna设备不支持播放列表功能，自己实现播放列表。提供播放列表创建、删除、查看、播放以及更新功能。
```
pysimpledlna playlist create -h
pysimpledlna playlist delete -h
pysimpledlna playlist view -h
pysimpledlna playlist list -h
pysimpledlna playlist play -h
pysimpledlna playlist refresh -h
pysimpledlna playlist update -h
```

Windows右键支持
------
:one: 安装右键菜单
```
> pysimpledlnaW install
```

:two: 删除右键菜单
```
> pysimpledlnaW uninstall
```
:three: 播放视频
```
在包含mp4, mkv文件的目录上右键 -> DLNA Share，程序自动选择第一台DLNA设备播放目录中的视频
```