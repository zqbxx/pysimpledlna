# 编译
编译完成后加入环境变量可以在命令行中直接使用
## Windows
1. 安装Mingw64，将gcc配置到系统环境变量中或git bash中
2. 安装开发版本[Nuitka](https://nuitka.net/pages/download.html#id3 "Nuitka")
3. 下载代码
```bash
git clone https://github.com/zqbxx/pysimpledlna.git
git clone https://github.com/zqbxx/prompt_toolkit_ext.git
```
4. 安装依赖
```bash
pip install -r ./pysimpledlna/requirements_app.txt
```
5. 编译
    - 编译依赖模块<br/>
        依赖模块只需要编译一次，用于缩短编译主程序时间
        - 新建一个临时目录`dep`
        - 从`site-packages`目录下复制`bottle.py`文件和`prompt_toolkit`目录到`dep`目录
        - 从`./pysimpledlna/complie`目录复制`compile_dep.sh`到`dep`目录
        - 编译<br/>
        打开git bash，进入`dep`目录
            ```bash
            ./compile_dep.sh
            ```
            将编译完成的`bottle.*.pyd`和`prompt_toolkit.*.pyd`复制到`./pysimpledlna/complie`目录
   - 编译pysimpledlna<br/>
       打开git bash，进入`./pysimpledlna/complie`目录
        ```bash
        ./complie.sh
        ```
6. 配置环境变量
将`pysimpledlna.exe`文件所在的目录加入到环境变量PATH中，启动新的命令行，输入[命令](usage.md)使用


