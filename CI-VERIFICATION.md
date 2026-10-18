# 干净环境复现记录

2026-10-18回查：运行38368747428（提交
9916d7584d591b097a7a61b66bd7426c4db9d6a7）的portable-tests和
fixed-kernel-build均已完成且success，包含新增的覆盖层集成测试。
此状态证明工具测试和内核编译通过，不代替设备启动验证。

首轮GitHub运行： https://github.com/yys235/l36h-ubuntu-touch/actions/runs/38365035808

对应仓库提交7520a9838fff561d0190073b1022d136e613caa7，Ubuntu24.04运行器。
portable-tests和fixed-kernel-build两个job均success。实际执行固定kernel
提交、汇总补丁、固定GCC4.9检出、Python2.7.18源码构建与完整zImage编译。
不是仅检查文件存在或构建脚本语法。

下载的zImage SHA256：
bc5e01f3dc4d2c950f61d542a77ae1e3b2104e6fa16d75992a1bc15e944852f9。
构建日志计算出的.config SHA256：
291f69b0ef18c53c8018b35fbbaeaf89627216b7ab7c3c71368c1c5f51fa06f6，
与公开最终配置一致。

首轮upload-artifact默认排除隐藏文件，.config未包含在下载包中。
已核对固定版本action参数并添加include-hidden-files:true，重新验证的
运行38366464641也已完成，两个job均success。下载的新产物包含实际.config，
直接计算SHA256与公开最终配置相同。新zImage SHA256为
bd81340ba1ddf733c19a69800ee0c50301a7160761f2babbb165f5c4559d975c。

该CI zImage和之前实机候选的哈希不同。Linux构建时间、版本和构建环境
等可能影响二进制；本轮没有建立逐字节可重复构建的保证。CI程序是新的
编译产物，尚未打包到boot并在实机刷入验证，不能复用旧镜像的实测结论。

原实机候选kernel SHA256为
cd989fd0a37f5809207c044ff4658b5d0e5b9ce0041ae890ef1223a2832e93d2；
它的对应源码和配置已导出，公开镜像选择仍需完整打包/安全/设备验证。
