# Sony设备树固定源码与本地差异

sources/device-tree-inventory.json记录yuga、fusion3-common和common源码
归档的提交、大小和SHA256。三者HEAD均与228项resolved manifest一致。

yuga有一处已捕获的本地修改，见patches/device-yuga-working-tree.patch：
BoardConfig.mk追加console=tty0及datapart=/dev/mmcblk0p26。
分区参数来源于已测L36H，不能认为所有设备编号都相同；首次安装必须
根据本机by-partlabel核对，指南已说明这一前提。

yuga还使用了未跟踪的initramfs.gz，其SHA256为
91b3e166edaeeae323ba2f34af2342533072b20a68cc7607599c50ebde499ce4，
与公开修补器的已测输出相同。应由固定原始initrd和helper生成，而不是
在manifest遗漏后静默下载continuous版本。

fusion3-common和common当前源码工作树干净。对应厂商库不包含在这些
设备树归档中；vendor来源、许可与完整Android容器构建仍需单独整理。
这些归档不能独立生成匹配驱动容器，Android构建环境和额外修复尚待整合。
