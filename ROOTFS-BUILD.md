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
覆盖层集成及首次启动准备工具已提供，见FIRSTBOOT.md；仍缺完整安装
流水线和实机复现，不能仅凭此脚本就刷写新设备。

2026-10-18实际构建验证：从固定官方输入完整提取后，应用当前公开的
10个覆盖层文件及LXC配置修改，构建3221225472字节的独立测试镜像。
e2fsck 1.47.2五轮检查退出0，镜像SHA256为
37818e27c999839904184c9c2da94cc19294be5b0e566e5052b875cd220fb4c2。
debugfs回读确认LXC配置含lxc.tty.max = 0及lxc.console.path = none。
该镜像仅验证真实根文件树的集成与镜像生成，不是可刷写发行资产：
首次启动身份、完整设备配置、匹配Android容器及实机启动验证仍待完成。

2026-10-20另从官方输入新建首次启动测试树，集成初始化服务、SSH策略和
服务器模式，单独组装三个userdata载荷文件。修复审阅发现的挂载只读检查
和父目录同步问题后，重建r3测试镜像：3221225472字节，SHA256为
078c097295e0ddf2d1d3dfbec5d45f7f3e2f948489382b1fa63241be1cb0cd2a。
只读e2fsck五轮检查退出0。此镜像未刷入手机，也未通过ARM sshd或冷启动
验收；个人化测试载荷不作为通用发行资产。完整边界见FIRSTBOOT.md。
