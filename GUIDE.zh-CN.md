# L36H Ubuntu Touch 安装与恢复指南

> 文档正在整理。匹配镜像、救援入口和安装器尚未形成正式 Release，
> 目前不能仅照本页完成整机刷写。缺少的步骤明确列在文末。

## 支持范围与准备

目标设备是 Sony Xperia Z L36h，设备代号 yuga、APQ8064、ARMv7。
不是 Xperia Z1/ZL 或其他 fusion3 设备。当前系统基线为 UT20.04.6 ARMHF；
不支持据此直接刷24.04镜像。需要已解锁引导加载器、可用USB数据线及
电脑上的Android Platform Tools。解锁流程和恢复资料须对应自己的设备。

本适配仍有历史内核panic、部分硬件未完整验证。它是实验性移植，
不能以短测通过宣称长期服务器稳定。相机在本部署中禁用。

在刷写前备份自己的数据，并准备匹配本机的原厂恢复途径。
TA、校准、IMEI、bootloader和其他设备身份不得复制自另一台手机。
Release不提供其他设备的这些分区，也不提供作者的账号或私钥。

## 识别连接与设备

本机实测进入fastboot：长按电源+音量上直到三次振动关机，拔USB，
按住音量上插入USB，蓝灯表示fastboot。按钮步骤需要按设备实际状态执行。

```text
fastboot devices
```

确认只连接目标设备，后续命令使用 `fastboot -s YOUR_SERIAL ...`。
不要把文档中作者设备序列号作为默认参数。部分Sony fastboot分区容量
查询为空，不能据此假定分区不存在或随意选择编号。

## 镜像布局与完整性

当前实机不是把整套rootfs直接刷到system分区：

| 组件 | 实际安装布局 |
|---|---|
| Android boot格式启动镜像 | boot分区；本机by-partlabel/boot解析为mmcblk0p17 |
| UT根系统 | userdata内的rootfs.img，3GiB，启动后loop挂载为根目录 |
| Android硬件容器 | userdata内的system.img，2GiB |
| 用户数据和系统可写区 | userdata；本机by-partlabel/userdata为mmcblk0p26 |
| 可选Hermes | 外接ext4 TF卡，单独挂载在/userdata/tf-card |

以上分区编号只是已测设备证据，安装器必须再核对本机分区标签。
rootfs.img 不得直接刷到约2GiB的system分区。TF卡也不是内部userdata。

下载同一Release配套文件后，对每个文件核对完整字节数和SHA256。
Windows可使用 `Get-FileHash -Algorithm SHA256 文件`；Linux使用
`sha256sum 文件`。校验失败或下载不完整，不继续刷写。
现有历史镜像的校验值不是最终发行清单，不混用不同诊断轮次。

原始官方通用rootfs输入的信息见rootfs-input.json，归档与签名保留在
assets/。该479463512字节归档不是可直接写入userdata的ext4 rootfs.img；
它需要保留Unix元数据提取，再创建文件系统并集成yuga覆盖层。
scripts/extract_touch_rootfs.py及8项测试已加入，要求Linux文件系统和
适当的chown/xattr权限，不在Windows目录中直接作为手机根系统使用。
签名信任链需要在正式流水线再次验证；哈希匹配不等同于签名验证。

## rootfs与容器传输

镜像应通过匹配救援环境上传到已核对挂载的userdata目录。发行脚本中
receive-ut-image.sh只从stdin接收文件，send-ut-image.py负责TCP发送；
它们不自动挂载分区、不建立救援SSH、不识别设备，更不会格式化。

传输只有收到完全匹配的 `COMMITTED 文件名 字节数 SHA256` 才算提交成功；
必须回读验证。只收到READY、电脑发送完毕或文件出现都不足以证明完整。
中断留下的.part不得改名为最终镜像使用。接收器拒绝长度/哈希不匹配，
重复传输可在匹配已有文件时返回ALREADY_COMMITTED。

安全救援连接、接收监听启动与首次安装流水线仍待集成，当前不要自行
将接收脚本的目录参数指向原始块设备。

## 系统修复与服务器模式

发行覆盖层需要与匹配rootfs集成，包含数字Android设备权限、sysfs调整、
LXC禁用console、WLAN初始化、蓝牙SMD、upower兼容和真实LM3533背光。
键盘另外需要libpinyin对齐修复库。只刷boot不会自动安装这些系统文件。

服务器模式是可选项：关屏只关闭背光，持有系统wake lock，保持后台CPU、
网络、SSH及Hermes运行，屏蔽sleep/suspend/hibernate/hybrid-sleep targets。
普通移动使用可选择不启用。手动关屏和唤醒应实测，不能只看sysfs缓存值。

首次启动准备与独立userdata载荷见[FIRSTBOOT.md](FIRSTBOOT.md)。初始入口为
root SSH公钥登录，端口22，禁止密码认证；安装者自备公钥，设备生成自己的
主机密钥。不复用作者账户、锁屏密码或diagnostic-authorizedkeys。

## 可选TF卡与Hermes

使用ext4卡，记录自己的UUID；格式化会清除该卡，应先识别外接设备并备份。
安装器不可硬编码作者卡的UUID或把内部mmcblk0当成待格式化外接卡。
Hermes启动器校验顶层实际挂载身份，缺卡时拒绝运行。

Hermes固定源码及依赖材料见hermes/README.md。系统Python保持不变，
ARMv7运行时和原生库放卡上。HTTPS可选：外部9119代理到本机9120，
新设备生成自己的CA及证书，其他电脑信任公开根证书；CA私钥不分发。
用户数据使用官方backup/import迁移，不发布会话或凭据。

## 恢复与发行前缺口

若系统无法启动，重新进入本机fastboot，使用保留的匹配boot恢复。
如果还要恢复原厂系统，使用自己设备对应的原厂恢复方案，不采用其他
用户的TA/校准镜像。正常运行中不要卸载正在提供rootfs/容器的userdata。

正式Release前还必须完成：

- 匹配boot/rootfs/system及匿名化覆盖层的完整产物和校验清单。
- 首次救援进入、镜像传输、挂载和刷写的一体化流程。
- 首次启动初始化的实机验收（准备工具和隔离测试已完成）。
- 冷启动复现、TF自动挂载、服务器模式及Hermes启动验证。
- 源码/依赖归档、对应许可证、干净构建验证和远程资产回读。

本页明确记录缺口，不把尚未生成的文件或未运行步骤作为已完成安装流程。
