# Sony vendor来源与校验

实际来源为TheMuppets/proprietary_vendor_sony，固定提交
fd7901fc26c1aee86a776a78f745f161f1d9db93。只使用yuga/与fusion3-common/。
公开目录中的sources/sony-vendor-selected-tree.json保存207个文件的路径、
字节数及Git blob SHA1；207个文件共102909279字节，实测逐个校验通过。

参数化校验入口：

```bash
python3 scripts/verify-vendor.py --root VENDOR_SONY_DIRECTORY \
  --manifest sources/sony-vendor-selected-tree.json
```

这证明当前文件与选定commit tree一致，不证明厂商二进制都是开放源码。
本目录没有将proprietary blobs作为开放源码重新授权；镜像和文件的
再分发声明、逐文件许可、可从原设备提取的替代方法仍需汇总。
正式发行构建必须明确依赖该固定输入，不同步其他Sony设备的全部库。

Android构建使用JDK8u504-b01、Python2.7.18、旧Bison及私有兼容主机库，
不是系统默认JDK/Python3。完整版本锁与包归档仍待核对。
