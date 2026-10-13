# 固定设备权限生成输入

对应项目版本见 ../halium-resolved.xml，文件保留上游版权和许可证声明。

| 文件 | 上游项目/提交 | 原始路径 |
|---|---|---|
| android_filesystem_config.h | Halium/android_system_core `48a959c59d5df019cde7d22e582fc5062443b7bf` | include/private/android_filesystem_config.h |
| ueventd.qcom.rc | Halium/android_device_sony_fusion3-common `e5a1dcf2220cef0ac40964f115540b8a35111c46` | rootdir/ueventd.qcom.rc；原始路径待对照源码归档再次核实 |

权限生成器使用数字 Android UID/GID，不能把 Ubuntu 账号名称直接代入。
输入副本不包含用户账号、Wi-Fi 或手机校准数据。
完整上游源码归档与再分发许可证汇总仍在整理。
