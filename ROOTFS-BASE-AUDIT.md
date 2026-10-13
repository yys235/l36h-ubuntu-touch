# 运行系统与官方基线程序对照

在原实机与已保留的官方rootfs提取目录中比较以下5个文件，SHA256全部相同：

| 文件 | SHA256 |
|---|---|
| /usr/sbin/repowerd | dd32a82fdadc50d51c891ce347efefc6ac1ce1030e2f1dbb8c58932a7a0dec2a |
| /usr/sbin/usb_moded | f26333acaaf9ccd067bfe030fa4753a041993b1e83635b9f474e61f1f3119f31 |
| /usr/libexec/upowerd | 2b12d49353d3f6f174e9737edec730c9f9949cfcb19691e4406b36853669f217 |
| /usr/sbin/lomiri-system-compositor | d834c9f7083ed3bfca32f92c7da1ddbc9a69bc7a854b2d3c36c5c754df98f2cd |
| /usr/sbin/lomiri-system-compositor.sleep | 85d29e5cbd66f0aeead6abd541cf90ed77eb8a5f0ee109d3b3733316efad57ea |

包版本记录：

- repowerd：2023.07+0~20240709171013.1+ubports20.04~1.gbp6fbd10
- usb-moded：0.86.0+mer67-0ubports1+0~20250313102759.3+ubports20.04~1.gbp20113b
- upower：0.99.17-1ubports1~20231212234457.1~f1ec857
- lomiri-system-compositor：1.0.0+0~20230608072212.7+ubports20.04~1.gbp142015

此结果排除了这些指定程序需要复制私有修改二进制的情况；对应服务
配置、内核和实际背光端点修复仍必须集成。该对照只覆盖5个文件，
不宣称整个运行rootfs与基线相同，也不覆盖libpinyin修正版或其他软件。
正在使用的手机rootfs含账号/密钥等私有状态，不直接克隆为公开发行镜像。
