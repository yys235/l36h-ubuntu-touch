# 键盘修复库重建记录

2026-10-20在独立目录从原始libpinyin2.3.0归档重建成功。输入清单、
开发包版本和SHA256、精确版本对应源码URL、构建机工具版本及产物信息
见[build-inputs.json](build-inputs.json)。组合包为
`keyboard-build-inputs-libpinyin2.3.0.tar.gz`；先核对整个归档哈希。

它包含libpinyin源码、两份补丁、三个ARMhf开发包和glib2.0/db5.3/glibc
各自的.dsc、上游源码及发行补丁。源码组件哈希已按.dsc核对；.dsc与
Ubuntu签名源索引的关联尚未验证，构建工具链完整源码归档也尚未闭合。
这不是“所有构建材料均已离线化”的声明。

## 重建顺序

在Linux amd64构建机安装清单所列版本的交叉编译器和Autotools，准备
按FIRSTBOOT.md从固定官方输入提取的rootfs目录。以下路径使用绝对路径，
工作路径避免空格。`ROOTFS`是提取后的`stage/system`，不挂载手机分区。
输入包解压后的当前目录含sources/、development/和patches/。

```bash
set -eu
export ROOTFS=/ABSOLUTE/PATH/TO/stage/system
export BUILD_ROOT="$PWD"
python3 - <<'PY'
import io, os, pathlib, subprocess, tarfile
work = pathlib.Path(os.environ['BUILD_ROOT'])
root = pathlib.Path(os.environ['ROOTFS']).resolve(strict=True)
deps = work / 'deps'
deps.mkdir(exist_ok=False)
for name in ['glib-dev.deb', 'db-dev.deb', 'libc-dev.deb']:
    data = subprocess.check_output(['dpkg-deb', '--fsys-tarfile', str(work/'development'/name)])
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        # 丢弃发行包中指向系统绝对路径的链接；需要的三个库入口稍后重建。
        members = [m for m in tar if not (m.issym() and m.linkname.startswith('/'))]
        tar.extractall(deps, members=members, filter='data')
with tarfile.open(work/'sources/libpinyin-2.3.0.tar.gz') as tar:
    tar.extractall(work, filter='data')
lib = deps/'usr/lib/arm-linux-gnueabihf'
for name, target in [
    ('libglib-2.0.so', 'usr/lib/arm-linux-gnueabihf/libglib-2.0.so.0.6400.6'),
    ('libdb.so', 'usr/lib/arm-linux-gnueabihf/libdb-5.3.so'),
    ('libm.so', 'lib/arm-linux-gnueabihf/libm.so.6')]:
    destination = root/target
    assert destination.is_file(), destination
    path = lib/name
    if path.is_symlink():
        path.unlink()
    else:
        assert not path.exists(), path
    path.symlink_to(destination)
(lib/'libc.so').write_text(
    'OUTPUT_FORMAT(elf32-littlearm)\nGROUP ( ' +
    str(root/'lib/arm-linux-gnueabihf/libc.so.6') + ' ' +
    str(lib/'libc_nonshared.a') + ' AS_NEEDED ( ' +
    str(root/'lib/arm-linux-gnueabihf/ld-linux-armhf.so.3') + ' ) )\n')
PY
cd deps
git apply --check ../patches/glibc2.31-gcc13-header.patch
git apply ../patches/glibc2.31-gcc13-header.patch
cd ../libpinyin-2.3.0
git apply --check ../patches/libpinyin-alignment.patch
git apply ../patches/libpinyin-alignment.patch
NOCONFIGURE=1 sh autogen.sh
export CC=arm-linux-gnueabihf-gcc CXX=arm-linux-gnueabihf-g++
export CFLAGS='-O2 -mno-unaligned-access' CXXFLAGS='-O2 -mno-unaligned-access'
export CPPFLAGS="-I$BUILD_ROOT/deps/usr/include/arm-linux-gnueabihf -I$BUILD_ROOT/deps/usr/include -I$BUILD_ROOT/deps/usr/include/glib-2.0 -I$BUILD_ROOT/deps/usr/lib/arm-linux-gnueabihf/glib-2.0/include"
export LDFLAGS="-L$BUILD_ROOT/deps/usr/lib/arm-linux-gnueabihf -Wl,--allow-shlib-undefined"
export GLIB2_CFLAGS="-I$BUILD_ROOT/deps/usr/include/glib-2.0 -I$BUILD_ROOT/deps/usr/lib/arm-linux-gnueabihf/glib-2.0/include"
export GLIB2_LIBS="-L$BUILD_ROOT/deps/usr/lib/arm-linux-gnueabihf -lglib-2.0"
./configure --host=arm-linux-gnueabihf --disable-static
make -C src -j2
sha256sum src/.libs/libpinyin.so.13.0.0
readelf -d src/.libs/libpinyin.so.13.0.0
readelf --version-info src/.libs/libpinyin.so.13.0.0
```

`filter='data'`需要提供该接口的Python版本，本次构建使用Python3.14。
原WSL1环境的GNU tar调用openat2返回ENOSYS；因此依赖包解包使用
dpkg-deb输出tar流及Python过滤器，而不使用失败的dpkg-deb -x路径。

头文件补丁仅作用于构建目录中的glibc2.31头文件，处理GCC13以上C++已
内建的_Float类型；不修改构建机或手机系统头文件。libc链接脚本也只在
该目录内重写，以引用官方rootfs的libc和加载器及开发包的nonshared库。

## 结果与部署边界

新构建产物610212字节，SHA256为
`eb368d13c0f895cdeba7f4b809464fe6cc21999032f2f847b57824dac4d023d3`。
SONAME为libpinyin.so.13，未嵌入RPATH/RUNPATH；glibc版本需求最高2.29。
所需库为glib2.0、db5.3、libstdc++、libm、libc、ARMhf加载器和libgcc_s。
静态检查不等于加载测试或中文输入验收。

上述文档代码块已原样提取，在组合包新解压目录执行（仅替换ROOTFS占位
路径），退出0，输出哈希与前述新构建结果一致。

此产物与README.md所记的原手机验证产物哈希不同，没有建立逐字节
可重复构建承诺。尚未向手机部署，也不直接覆盖系统libpinyin。
发行集成须使用私有路径与Maliit专用加载配置，并重新验证首字符输入、
英文/数字认证及会话稳定性。
