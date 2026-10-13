# 手机端HTTPS代理

官方Caddy2.11.7 ARMv7，源码提交72dd0fb067f6d7826c7f79907670ba4a713bfe37。
官方预编译归档SHA256为
492c730b1b992e0d3e4346d1652128ae6ad99208834d3d78c27b3b6c9541c841。
来源： https://github.com/caddyserver/caddy/releases/tag/v2.11.7 。
对应源码及依赖的归档仍待补齐，不包含作者CA私钥。

先固定或保留手机局域网IP，再生成自己的配置：

```bash
python3 scripts/render-https-config.py --host YOUR_PHONE_IPV4 --output generated-https
```

默认保持外部端口9119，内部Hermes仅监听127.0.0.1:9120。
生成器拒绝无效IP和相同的内外端口，不修改任何运行系统。

部署前在自己的HERMES_HOME/config.yaml中保留原有dashboard认证配置，
只更新 `dashboard.public_url` 为public-url.txt中的完整HTTPS地址。
这一步使官方Hermes在loopback后端仍启用远程访问认证，不可遗漏。

生成文件用途：Caddyfile放在HERMES_BASE/https/；HTTPS service放系统
systemd目录；web-backend.conf作为现有yuga-hermes-web.service的drop-in。
Caddy二进制放HERMES_BASE/native/caddy。备份旧配置，确认后端可以
启动后再切换9119监听；不要在原HTTP服务仍占用9119时启动同端口代理。
完整自动安装器和回退操作还在整理，当前生成器不是一键部署程序。

Caddy为本设备自动生成本地CA及IP证书，存储目录为
HERMES_BASE/https/data/caddy/pki/authorities/local/。
只将root.crt分发给客户端安装信任，root.key不得分发或上传GitHub。
每台新设备创建独立CA，不要导入作者手机的CA文件。

已测实机验证包括严格TLS校验、密码登录、安全Cookie、配置API和
带认证票据的WSS HTTP101升级。公开参数化配置仅完成生成器测试，
还未在新的设备上执行完整部署复现。
