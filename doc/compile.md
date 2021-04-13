# 编译
编译完成后加入环境变量可以在命令行中直接使用
## Windows
#####1. 安装Mingw64，将gcc配置到系统环境变量中或git bash中
#####2. 安装[Nuitka](https://nuitka.net/pages/overview.html "Nuitka")
#####3. 下载代码
```bash
git clone https://github.com/zqbxx/pysimpledlna.git
git clone https://github.com/zqbxx/prompt_toolkit_ext.git
```
#####4. 编译
进入./pysimpledlna/complie目录，右键-> `git bash here`
```bash
./complie.sh
```
#####5. 配置环境变量
将pysimpledlna.exe文件所在的目录加入到环境变量PATH中，输入[命令](02.usage.md)使用


