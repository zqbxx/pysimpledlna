# pysimpledlna

### 介绍
一个简单dlna投屏工具，参考和使用了以下项目<br/>
<https://pypi.org/project/dlna/><br/>
<https://pypi.org/project/nanodlna/><br/>
<https://github.com/cherezov/dlnap>

### 安装
```
git clone https://github.com/zqbxx/pysimpledlna.git
py setup.py install
```
### 命令行使用
- 查找DLNA设备
```
> pysimpledlna list
[ 1 ] Kodi (DESKTOP-O7IVEPH) @ http://192.168.199.151:1901/
```

- 播放视频
```
> pysimpledlna play -i test.mkv -u http://192.168.199.151:1901/
```

### Windows右键支持
- 安装右键菜单
```
> pysimpledlnaW install
```

- 删除右键菜单
```
> pysimpledlnaW uninstall
```
- 播放视频
```
在包含mp4, mkv文件的目录上右键 -> DLNA Share，程序自动选择第一台DLNA设备播放目录中的视频
```