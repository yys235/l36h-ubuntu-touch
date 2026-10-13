# Hermes ARMv7 部署材料（构建包待补齐）

源码固定为 NousResearch/hermes-agent
`71d34bad1045610252eda02ee79549436896e784`，官方源码未作应用逻辑修改。
此设备不支持官方 PM 自动下载的全部工具：不得把普通最新版本安装命令
视为已经验证过的 ARMv7 部署方案。

## 当前已锁定的环境

- 私有 Python3.14.8 ARMv7，发行信息见 ../sources/versions.lock.json。
- 原生依赖需兼容 UT20.04 的 glibc2.31；不得替换系统 Python 或 libc。
- 当前实机72个包的名称和版本见 installed-package-versions.json。
  这是运行快照，不是带发行文件哈希的 pip 完整锁文件。
- Anthropic 必须匹配此版源码要求的0.87.0；此前误装1.13.0会混用
  httpx/httpx2 Timeout类型。不能仅用 pip install -U anthropic 修复。
- 官方 Node20.20.2 linux-armv7l + 对应源码构建的 tui/dist/entry.js；
  HERMES_NODE 与 HERMES_TUI_DIR 指向私有运行时，避免 PM 自动安装失败。
- Web静态资源从同一源码版本构建。当前运行所需的完整依赖归档、编译
  配方与哈希校验仍在汇总，本文还不是完整安装指南。

## 卡挂载保护

hermes-tf-launch.sh 支持 /etc/hermes-server.env 中指定本机卡UUID。
使用示例配置时必须填入自己的UUID。启动器比对顶层挂载设备与 blkid
查出的设备身份，缺卡/错误挂载即退出72，不回退到内置存储继续写入。
该公开变体仅完成语法和缺配置拒绝测试，尚未替换手机上的运行启动器。
不要把作者手机的UUID、账号、主机密钥或CA私钥复制到新设备。

## 数据迁移与HTTPS

完整用户数据应使用官方 hermes backup 与 hermes import；不要直接迁移
ARMv7虚拟环境到其他CPU架构。模型凭据和会话均不属于公开发行内容。
可选HTTPS使用手机反向代理，外部9119，Hermes仅监听127.0.0.1:9120。
每台设备应创建自己的本地CA，访问电脑信任其公开根证书。具体参数化
HTTPS配置与自动安装流程待整理，不发布作者私有CA或固定LAN地址。
