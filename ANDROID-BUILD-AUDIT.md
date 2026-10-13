# Android源版本审计结果

android-source-audit.json已完成228项检查：全部HEAD匹配resolved manifest，
无读取错误，3个项目存在本地修改。

| 项目 | 固定提交 | 本地差异 |
|---|---|---|
| device/sony/yuga | 2e8bc5a8d4a22c90d3bf3170023e7acb627ca0d8 | BoardConfig.mk补丁；固定initramfs.gz |
| external/bison | 7467d52af437dd3dfea237a6865ab84bf258dee0 | lib/fseterr.c补丁；另有生成的.version/config.h.in与文档备份 |
| external/gpg | 0ff5187b51ef778746ce818cf06abae8cb1bb826 | cipher/dynload.c和include/config.h补丁 |

Bison/GPG源码归档已保留，补丁在当前修改树上通过反向context检查；
这不是完整重构建验证。Bison生成文件还需确认哪些构建需要，文档备份
不作为发行源输入。相关构建工具、环境参数和顺序仍待整合。

另行检出的halium-boot、外部kernel及vendor不能仅以这228项检查覆盖。
它们有独立固定版本/修改清单。代码审计已明确这些边界，不宣称一份
manifest本身就足够复现整套构建。
