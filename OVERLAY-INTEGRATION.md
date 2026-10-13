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
完整传入后已回读验证。提取仍在进行，尚未在本轮修改提取中的源树。
