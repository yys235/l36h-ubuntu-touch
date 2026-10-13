# 通用系统覆盖层（待集成验收）

这里仅存放不包含账号、密钥、网络密码或设备唯一标识的配置。
文件层级对应手机根目录，不表示目前可以直接整目录覆盖安装。

| 文件 | 原因 | 启用要求 |
|---|---|---|
| yuga-wlan-init.service | 初始化 PRIMA WLAN 的 con_mode | 匹配 yuga 内核，启用该 unit |
| upower.service.d/10-yuga-kernel.conf | 旧内核不支持服务使用的 PrivateUsers 隔离 | systemctl daemon-reload；不代表其他沙箱可全部禁用 |
| yuga-backlight-interface.service + repowerd drop-in | 将错误的通用 LED 接口映射到物理 LM3533 背光 | repowerd 启动前完成映射，启用 backlight unit |
| yuga-server-awake.service | 用户可选服务器模式，保持整机运行，屏幕仍可关闭 | 启用该 unit；服务器模式还需屏蔽 systemd 的睡眠 targets |

服务器模式需要屏蔽的 targets 为 sleep.target、suspend.target、hibernate.target、
hybrid-sleep.target。此模式保持 CPU/网络工作，耗电与常规手机待机不同。
默认移动使用场景不要未经选择就启用服务器模式。

运行系统的根文件系统通常只读；安装器须检查目标设备与挂载位置，保存原有
同名配置，临时 remount 后写入并恢复只读，不覆盖密码、身份或主机密钥。
目前发行安装器还在整理，本目录没有自动执行以上操作。

已加入蓝牙 SMD 初始化脚本与 service drop-in，以及 usb-moded 的 Sony
USB 描述符配置。LXC console 补丁在 ../patches/yuga-lxc-no-console.patch；
它需要应用到匹配 rootfs 内的 var/lib/lxc/android/config，不能只复制 patch。
设备权限规则和 sysfs 配置分别在 usr/lib/lxc-android-config 与 usr/lib/tmpfiles.d。

权限生成器及固定输入在 ../scripts 和 ../sources/inputs，生成命令为：

```bash
python3 scripts/generate-yuga-udev.py \
  --identities sources/inputs/android_filesystem_config.h \
  --ueventd sources/inputs/ueventd.qcom.rc --output GENERATED_OVERLAY
```

6 项规则测试通过；130条设备规则与27条sysfs调整重生成后逐字节相同。
这些检查不替代设备节点实际权限和冷启动硬件验收。
尚待纳入：键盘修正版库、相机禁用、USB模式/网络策略及 Hermes/TF卡的
完整参数化安装。不要把这份目录视为完整 rootfs 发行替代品。
