# 已测主机构建环境

Android7.1构建与Hermes原生依赖交叉构建属于不同环境，不共享默认工具链。

| 环节 | 实际工具 |
|---|---|
| yuga内核 | 固定GCC4.9预编译包，Python2.7.18包装器 |
| Android容器 | Temurin OpenJDK8u504-b01、Python2.7.18、GNU Bison2.7 |
| Android旧主机链接兼容 | 私有libncurses5/libtinfo5，版本6.2-0ubuntu2 amd64 |
| reboot helper | GCC15.2.0交叉编译，静态ARMhf；另有固定版本证据 |
| Hermes原生库 | ARMhf交叉编译器、Focal sysroot、私有库搜索路径，独立Python3.14 |

不修改系统全局Java/Python alternatives；使用构建shell内的JAVA_HOME、PATH
和私有LD_LIBRARY_PATH。旧build-focal.sh等历史脚本未作为通用安装器发布。
公开构建入口必须由安装者提供工具目录，不能继续依赖/home/pmos2。

sources/hermes-sysroot-cache.json将记录实际缓存的Debian包名、版本、架构、
源包字段、大小和哈希。缓存中存在包不等于全部被构建使用；依赖清理、
可重建sysroot流水线和对应源码再分发材料尚待完成。
不要把“已锁定环境记录”描述为已完成干净机器复现。
