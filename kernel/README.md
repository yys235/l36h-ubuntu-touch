# 内核对应源码材料（发布准备）

上游：`https://github.com/Halium/android_kernel_sony_apq8064.git`

固定基线提交：`3e373fec12898bacbcb93713732dbc26f5b3b3f5`。

`yuga-final-working-tree.patch` 将最终构建源码相对上述基线的修改汇总为
一个补丁，包括新增的 AppArmor 回移源码和蓝牙头文件。
`yuga-final.config` 从最终构建输出目录导出。

导出过程使用独立临时 Git index，未修改原构建工作树的 index。
这两个文件仍需在干净基线上验证应用，并核对最终 zImage 的构建对应性；
目前不得仅凭这些文件认定已经具有完整的可复现构建环境。

最终构建依赖旧 GCC 4.9 工具链及 Python 2 主机包装器，不能直接以系统
GCC 或 Python 3 替代。工具链归档、版本锁定、源码 bundle、打包工具和
干净环境构建说明正在整理。

内核源码遵循上游 GPL-2.0 等各文件许可证；保留对应源码原有版权声明。

本地已生成固定基线完整源码归档：
`../sources/kernel-base-3e373fec.tar.gz`，SHA256
`0880b3bfc246e0c3ae782f9221ebde28e48275e6af03845c2326f3e1a622f2b2`。
归档包含44515个目录/文件条目；结合汇总补丁可获得修改后的内核源码。
补丁在独立基线 index 上应用成功，结果 tree ID
`07328d79afdcf92919072de97c35c738eba4c544` 与最终导出源码一致。
此验证涵盖补丁完整性，不等同于干净环境编译或实机刷写通过。

参数化构建入口 `build-kernel.sh` 已加入；调用形式为：

```bash
bash build-kernel.sh SOURCE OUTPUT GCC49_ROOT PYTHON2_BIN_DIRECTORY
```

当前只验证了 Bash 语法，尚未执行新的干净环境完整构建。
GCC 4.9 归档固定到提交48ef1e67，含上游原有许可证和 NOTICE。
工具链对应源码的提交表保存为 gcc49-source-revisions.prop；其源码归档和
再分发审查尚待完成，不把预编译 GCC 包等同于完整工具链对应源码。
Python2 必须从包含校验值的 Python-2.7.18.tar.xz 构建；不能使用当前系统
python3 运行旧内核的 scripts/gcc-wrapper.py。

最终 diagnostic boot 候选已用 `verify-boot-repack.py` 提取 kernel/ramdisk 后
重打包，逐字节相同，SHA256 为
8ff079c06cc8b951345a576916343725cfc3ed4bc980e8e22d22e56406920020。
`mkboot.py` 随目录提供，Python3 标准库即可执行。
这只是打包正确性验证：候选带全局 SLUB 调试配置，不宣称生产稳定。
ramdisk 的有限标记扫描没有匹配到私钥/授权密钥标记；不替代完整内容审查。
安装基线 rootfs 是早期版本，尚需合并后续系统修复并完成匿名化，不能直接
作为与上述 kernel 匹配的最终发行系统发布。
