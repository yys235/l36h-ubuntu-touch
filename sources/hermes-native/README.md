# Hermes ARMv7 原生依赖源码

本目录保存实际构建阶段使用的源码发行包，archive-checksums.json
记录每个文件的SHA256和字节数。不是自动可安装的wheelhouse。

| 组件 | 版本 |
|---|---|
| cffi | 2.1.1 |
| psutil | 7.2.2 |
| Pillow | 12.3.0 |
| pillow-heif | 1.8.1 |
| httptools | 0.8.0 |
| firecrawl-anydoc | 0.2.4 |
| libheif | 1.23.6 |

这些包的许可证各自见归档内的 LICENSE/COPYING 等文件，不能把全部
依赖视为 Hermes 项目本身的许可证。

实机兼容的构建采用 Focal ARMhf sysroot，限制glibc要求不超过2.31。
宿主机编译器曾误引入宿主头文件和__ioctl_time64；修复依赖隔离头文件与
库搜索路径。专用交叉编译包装器、sysroot开发包的固定版本、libheif
codec依赖及最终原生库构建配方尚待导出和验证。

不要在手机上直接运行 pip install 最新版本来替代这个构建过程。
当前72项已安装版本快照位于 ../../hermes/installed-package-versions.json；
版本快照与本目录仍不足以证明所有Python依赖可离线安装。
