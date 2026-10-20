# 首次启动准备工具（实机验收待完成）

仅用于从固定官方UT20.04.6输入新建的yuga发行目录，不是现有手机的在线
升级脚本。已在真实官方文件树完成准备和ext4镜像构建；新初始化的设备
启动、公钥登录和重启恢复尚未通过，不能因此直接刷写新设备。

## 登录与身份

初始管理员入口是root的SSH公钥登录，端口22；禁止SSH密码和交互认证。
没有共享密码，也不复制作者主机密钥。安装者提供自己的OpenSSH公钥，
手机首次启动生成独立ed25519主机身份，后续启动保留身份与管理员维护的
authorized_keys。手机锁屏与phablet资料继续使用官方首次设置流程。

只接受单行ed25519/RSA/ECDSA公钥，拒绝私钥、多行、authorized_keys选项、
非普通文件及链接。私钥留在安装者电脑，工具不需要也不接收私钥。
当前配置AllowUsers=root，若以后增加其他SSH账号，需要管理员明确调整
并重新验证访问策略，不能把初始入口理解为已开放其他用户登录。

## Linux构建目录中的调用顺序

主机工具要求Python3.9以上、root权限、OpenSSH ssh-keygen及Linux文件系统；
已测试WSL主机。设备端初始化只用系统Python3.8及OpenSSH，不替换系统Python。
所有输出目录必须新建且不存在；先完成官方归档长度、哈希和签名校验。

```bash
sudo python3 scripts/extract_touch_rootfs.py OFFICIAL_ROOTFS_ARCHIVE STAGE
sudo python3 scripts/integrate-rootfs-overlay.py --root STAGE/system \
  --overlay overlay --userdata OVERLAY_DATA
sudo python3 scripts/prepare-yuga-firstboot.py --root STAGE/system \
  --userdata FIRSTBOOT_DATA --public-key YOUR_OWN_PUBLIC_KEY.pub
sudo python3 scripts/assemble-yuga-userdata.py --overlay-data OVERLAY_DATA \
  --firstboot-data FIRSTBOOT_DATA --output USERDATA_PAYLOAD
sudo python3 scripts/build-rootfs-image.py --source STAGE/system \
  --output EXISTING_BUILD_DIRECTORY/rootfs.img
```

服务器用途在prepare-yuga-firstboot.py命令明确追加`--server-mode`；这会
启用awake并屏蔽四个睡眠target。默认模式不做这些改变。
Wi-Fi初始化和真实背光接口服务在两种模式下均启用。
准备工具仅允许已核对的官方SSH配置；未知或修改过的片段、已有SSH服务
覆盖项、源镜像中的主机身份均拒绝。官方只读元数据和/lib→usr/lib别名
允许在镜像范围内解析，所有写入路径仍禁止符号链接。

## 两个输出不能混淆

rootfs.img包含系统文件及服务；USERDATA_PAYLOAD单独包含：

- yuga-port/bluetooth-init.sh
- yuga-firstboot/input/authorized_key
- yuga-firstboot/input/config.json

这三个文件最终须安装在目标真实/userdata的对应路径。装入rootfs.img的
隐藏userdata目录不会生效。组装器拒绝缺少蓝牙脚本、旧设备状态或额外文件，
避免把使用中的userdata、模型凭据和私钥当成发行载荷。
载荷包含安装者公钥，不应把自己的个人化载荷作为通用Release发布。
当前工具不挂载、格式化、传输或刷写手机；这些步骤仍需完整安装器集成。

## 设备端失败处理和持久化

初始化服务等待/userdata、/root、/etc/ssh，检查三个真实可写ext4挂载点
属于同一userdata设备；不满足时不放行SSH。输入及状态须root所有，禁止
组/其他用户写入，私钥和authorized_keys使用严格私有权限。
sshd有效配置必须为22端口、公钥认证、无密码/交互认证，才提交成功标记。

已核对原始initramfs：scripts/halium的process_bind_mounts在mountroot中
执行；/etc路径立即绑定，/root写入生成的fstab，后续由本地挂载阶段处理。
因此不假设所有持久化路径都在/sbin/init之前挂载完成，unit显式要求这些
挂载点，运行时也复查。初始化同时准备sshd的/run目录，供启动前配置检查。

标记为/userdata/yuga-firstboot/status.json。正常重启不覆盖管理员修改过的
authorized_keys，不重新生成已有主机密钥。标记存在但密钥、授权文件或
输入损坏/丢失时拒绝继续；不要删除input目录作为日常清理步骤。
失败会写入该unit日志，保留本地UT与救援入口，不格式化或重置设备身份。
故障恢复应检查保存的日志及文件权限，不以复制其他手机私钥或开启密码
认证来绕过校验。

## 验证边界

准备、运行时文件操作和组装测试使用隔离目录及真实ssh-keygen。它们未
启动主机SSH，也不修改主机账号。目标ARM sshd的模拟执行在此WSL环境
遇到guest address mapping错误，不能列为通过。实机首次登录、拒绝密码、
重启指纹不变、关屏持续运行与Wi-Fi/背光验收仍是发行前必须完成的项目。
