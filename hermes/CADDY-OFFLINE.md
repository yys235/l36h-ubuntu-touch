# Caddy离线构建输入

草稿资产`caddy-offline-build-inputs-72dd0fb0-go1.26.0.tar.gz`包含固定主模块
源码、Go1.26.0 Linux amd64编译器及对应Go源码、595个模块的下载缓存。
包长和SHA256见`sources/caddy-offline-build.json`，模块逐文件清单见
`sources/caddy-offline-modules.json`。保留各源码归档中的许可证。

以下操作在Linux amd64构建机的新工作目录执行，不在手机运行编译器：

```bash
# 先按公开清单校验整个输入包，再解包；不要使用未知来源的归档。
mkdir caddy-build
cd caddy-build
tar -xzf /PATH/TO/caddy-offline-build-inputs-72dd0fb0-go1.26.0.tar.gz
tar -xzf toolchain/go1.26.0.linux-amd64.tar.gz
tar -xzf source/caddy-72dd0fb0.tar.gz
export GOTOOLCHAIN=local
export GOPATH="$PWD/gopath" GOMODCACHE="$PWD/module-cache" GOCACHE="$PWD/build-cache"
export GOPROXY=off GOSUMDB=off
export GOOS=linux GOARCH=arm GOARM=7 CGO_ENABLED=0
export GOMAXPROCS=2 GOMEMLIMIT=1GiB
export PATH="$PWD/go/bin:$PATH"
cd caddy-72dd0fb067f6d7826c7f79907670ba4a713bfe37
go build -mod=readonly -trimpath -buildvcs=false -p 2 -o ../caddy-armv7 ./cmd/caddy
```

已验证已有缓存及从归档重新展开的全新模块/编译缓存两次断网依赖构建，
都使用原始上游go.mod/go.sum，产生相同二进制。
下载全部模块时Go会增加go.sum校验项；验证构建前已恢复上游原文件，
确认两文件与公开哈希相同，构建过程未改变它们。595个模块包含工具和
测试依赖，不能把数量理解为实际二进制链接的模块数。

归档内部manifest记录打包时状态，后续全新缓存重建结果以公开的
caddy-offline-build.json为准。当前75,904,221字节交叉编译产物未在ARM上
执行，未部署手机；其SHA256
仅记录构建证据，不承诺与官方发行二进制相同。现有手机使用官方二进制。
