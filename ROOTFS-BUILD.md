# ext4根镜像构建入口

scripts/build-rootfs-image.py将已经准备好的Linux目录构造成ext4镜像，
不执行提取、覆盖层集成、挂载、格式化设备或刷写。

```bash
python3 scripts/build-rootfs-image.py --source PREPARED_SYSTEM_DIRECTORY \
  --output NEW_OUTPUT_DIRECTORY/rootfs.img
```

默认3GiB，输出目录必须存在且有完整镜像大小+256MiB的空闲空间。
拒绝已有镜像或.part，拒绝把输出放在源树内部。先生成.part，mke2fs与
只读e2fsck成功后计算SHA256，最后改名；失败产物不作为最终镜像。

文件系统特性显式列出，而不继承新主机的mke2fs.conf默认现代特性。
32MiB合成目录实际构建、e2fsck及debugfs回读通过；没有64bit、
metadata_csum、metadata_csum_seed、orphan_file、encrypt或casefold。
该结果不代替真实3GiB UT镜像构建、旧内核挂载和冷启动验证。

准备源树仍需固定官方rootfs、元数据保留提取、完整覆盖层和首次启动
匿名化流程。rootfs用户身份/主机密钥不从正在使用的手机复制。
源归档含约1.7GiB文件；从头准备目录和镜像需要至少数GiB额外空间，
本发布流程建议提供10GiB工作空间。完整Android干净构建还会需要更多。
现在仍缺完整覆盖层集成和实机复现，不能仅凭此脚本就刷写新设备。
