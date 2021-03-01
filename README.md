pysimpledlna
=====

介绍
------
一个简单dlna投屏工具，参考和使用了以下项目<br/>
<https://pypi.org/project/dlna/><br/>
<https://pypi.org/project/nanodlna/><br/>
<https://github.com/cherezov/dlnap>

安装
------
```
git clone https://github.com/zqbxx/pysimpledlna.git
cd pysimpledlna
py setup.py install
```

命令行使用
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
计划完成的功能
------
- [ ] 播放列表
  - [x] 创建
  - [x] 删除
  - [x] 播放
- [x] 播放列表播放器
  - [x] 播放列表播放器切换播放列表中的视频
  - [x] 播放列表播放器暂停、停止、前进以及后退等常用功能
- [ ] 手机控制
  - [ ] 实现web ui
  - [ ] 手机扫码连接