# initramfs 打包与内容清单

ramdisk-inventory.json 列出最终已测boot候选的351个CPIO条目、模式、UID/GID、
大小与文件哈希，不输出文件内容或凭据。它属于有限审计，不是完整安全证明。
未匹配私钥/授权密钥文件，存在 scripts/panic/telnet 救援路径。

发行前须核实这个路径仅在预期panic/recovery条件下启动、监听地址和
root shell认证方式。不能因为文件名是panic就假定不会暴露网络入口。
当前还没有把该boot候选作为正式发行镜像发布。

scripts/patch-halium-initrd.py 保留上游CPIO元数据，在RNDIS functions写入
之前设置wceis，添加reboot-bootloader helper。新命令入口为：

```bash
python3 scripts/patch-halium-initrd.py \
  --source UPSTREAM_INITRD.gz --helper reboot-bootloader-armhf \
  --output yuga-initrd.gz
```

输出必须是新文件。helper源码见scripts/reboot-bootloader.c；上游initrd
固定源码版本、生成配方和helper完整编译配置仍待整理。
3项补丁测试通过，公开CLI重生成后的解压CPIO与已测ramdisk逐字节相同。
原始输入归档保存于assets/halium-initrd-armhf-input.gz，哈希在版本清单中。

实际额外使用的halium-boot项目固定提交499ea587183ea9407a0ccce64013b6cfa80d0efe，
源码归档已纳入sources；它不在228项resolved manifest中，不可遗漏。
该项目get-initrd.sh默认下载continuous发行的浮动initrd，公开构建不能
继续依赖这个浮动URL，必须使用清单内固定哈希的本地输入。
当前checkout状态干净，其导出的working-tree.patch为空；不需应用空补丁。

helper实测编译器标记为GCC15.2.0，主机包为gcc-15-arm-linux-gnueabihf
15.2.0-16ubuntu1cross1，静态libc开发包2.43-2ubuntu2cross1。已测二进制是
静态ARM EABI5，声明Linux3.2最低ABI；不能仅凭静态链接认定任何新版本
编译器/运行库生成的程序在3.4内核上可用。模拟syscall契约测试通过，
未在本轮调用真实重启。完整原始编译参数与对应运行库来源仍待整理。

实际telnet脚本使用 `telnetd -b 192.168.2.15:23 -l /bin/sh`，无密码shell，
先配置USB RNDIS和USB子网DHCP。scripts/functions的panic函数执行
scripts/panic目录。此证据说明代码绑定救援USB地址，不证明所有panic
调用和现场网络隔离均已测试，也不把它视为经过认证的远程管理入口。
正式服务器远程管理使用单独配置的SSH；公开版应明确分离救援与正式模式。

主机只剩约2.2GiB可用空间，官方rootfs提取数据约1.7GiB，构建文件系统
还需要额外空间。不能在该条件下盲目提取并承诺完整发行镜像生成成功。
源归档已保留，下一阶段需要足够空间的构建位置或经验证的替代构建流程。
