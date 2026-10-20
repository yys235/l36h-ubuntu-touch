# libpinyin ARM 对齐修复

Maliit 首字符输入崩溃的已确认原因：libpinyin 2.3.0 对序列化词频字段执行
未对齐 guint32 读取，在 ARMv7 上生成 VFP 加载，触发 SIGBUS。
修复使用 memcpy 复制到对齐的局部变量，保持字典格式与 ABI。

固定源码为 `../sources/libpinyin-2.3.0.tar.gz`，SHA256：
`00cb09f267031fb528bebc4621268037fca64677040123ebb184a50afcb43430`。
许可证和版权见源码的 COPYING 等原有文件。

```bash
cd libpinyin-2.3.0
git apply --check /path/to/libpinyin-alignment.patch
git apply /path/to/libpinyin-alignment.patch
```

补丁在源码归档中的原始 phrase_index.h 上已验证可应用；标准相对路径
不依赖作者电脑。`patch-pinyin-alignment.py SOURCE_DIRECTORY` 是等价的
严格匹配修补脚本，两种方法只选一种，不能重复应用。

构建使用固定Focal ARMhf glib/数据库开发头文件和匹配运行库，以及
`-mno-unaligned-access`。新目录重建已通过，完整命令、旧头文件兼容
补丁和依赖清单见[BUILD.md](BUILD.md)。开发依赖对应源码已取得，
完整构建工具源码闭包和新产物实机输入验收仍待完成。

原实机修正版库 SHA256：
`9310425bcca56df5cf6173f6500209540a0cbb97638491eb4af30a6133041204`。
当时以 Maliit 专用 LD_PRELOAD 加载，不替换系统 libc/libstdc++。
发行部署路径和对应库产物尚待整合，不包含用户输入历史或字典缓存。
