# 覆盖层集成入口

scripts/integrate-rootfs-overlay.py在Linux root权限的构建目录中运行：

```bash
python3 scripts/integrate-rootfs-overlay.py --root STAGE/system \
  --overlay overlay --userdata NEW_USERDATA_STAGE
```

要求根系统已完整提取，存在官方os-release和匹配的LXC配置。
etc/和usr/文件进入rootfs；userdata/文件进入单独的新输出目录，不能
藏入rootfs.img后误以为实际userdata挂载点已经安装了这些文件。
所有目标检查完成后才开始写入，拒绝越界符号链接、已有userdata输出、
未知命名空间或不匹配LXC配置。不会对正在运行的/根目录执行安装。

已在合成目录验证3项测试：分离userdata及LXC修改、越界拒绝、已有
userdata保留。它还不启用systemd服务、不初始化账号/SSH身份、不生成
TF挂载配置，也不包含所有后续组件。完整发行流水线必须明确完成这些
步骤后再生成/刷写镜像，不能仅凭该工具退出0认定发行rootfs已就绪。

手机构建区为单独的yuga-release-build-r1目录；官方输入长度479463512，
哈希44c0e3a6efb26be826d79df6bccf5371b540e42eb2aeb1bf46c010db5fbdd975，
完整传入后已回读验证。该手机构建任务暂停后未继续依赖其状态。

2026-10-18在独立的WSL构建目录从固定官方输入重新完整提取，得到
47226个普通文件（1704145094字节）、10454个符号链接和148个硬链接。
随后真实根文件树集成成功，共复制10个覆盖层文件，LXC控制台修改成功；
userdata脚本进入独立目录。合成目录3项测试本轮再次通过。
由该目录生成的3GiB测试镜像通过只读e2fsck；详见ROOTFS-BUILD.md。
这些结果尚不包含服务启用、首次启动初始化或实机冷启动验收。

后续首次启动准备和服务启用由独立工具处理，见[FIRSTBOOT.md](FIRSTBOOT.md)。
该流程已完成真实官方文件树集成及新镜像检查，实机冷启动验收仍待完成。
