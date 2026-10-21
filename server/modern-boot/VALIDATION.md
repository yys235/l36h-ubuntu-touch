# Modern boot validation status

This is a hardware bring-up branch. Ubuntu26.10 is not yet installed as a complete server.

- Fixed APQ8064 kernel CI [39398776562](https://github.com/yys235/l36h-ubuntu-touch/actions/runs/39398776562): passed, Linux7.2.0-yuga-modern-probe, Clang18.1.3.
- All downloaded artifact sizes/SHA256 independently verified.
- 13 existing test suites and 26 initial new boot/input/initramfs tests passed; subsequent GPIO26, key, SSH-policy and PID1 handoff tests bring the new total to39.
- Independent code review found no actionable issue before the first hardware flash.
- First hardware boot: actual uname7.2.0-yuga-modern-probe, four CPUs, approximately2GiB RAM, Windows RNDIS driver bound, DHCP assigned host172.16.42.2, phone172.16.42.1 private telnet executed commands.
- eMMC and GPT detected. Internal storage is mmcblk1 in this kernel, whereas old3.4 used mmcblk0. Installation must resolve partition identity and size, not reuse device numbers.
- TF probe failed with GPIO26 pin ownership conflict. Controlled DTB derivative removes only `function="gpio"` from the card-detect pinconf node, preserving pinconf and GPIO descriptor handling. Kernel/modules remain identical to CI; derivative provenance is explicit. Sorted decompiled DTB diff contains exactly that one removed property. Follow-up review found no concrete issue; corrected configuration subsequently booted twice with USB and TF available.
- First diagnostic boot had only DRM device, no panel/fb, no touch input, no power_supply entries; SoC thermal readings were available. Wi-Fi firmware was absent. These are incomplete hardware support, not completed server functionality.
- First experiment ended within five minutes. Old diagnostic boot was restored by checking boot PARTNAME/size, validating source SHA256 and matching a complete-length readback SHA256. Old3.4 uname and charging were confirmed afterward.
- Second hardware boot with GPIO26 fix: Windows RNDIS/DHCP/telnet worked; eMMC mmcblk1 and64GB SDXC mmcblk0/p1 detected, previous GPIO ownership error absent. The run ended around135seconds, recovery boot source/readback hashes matched before reboot. Third hardware boot repeated this corrected configuration successfully. Storage enumeration changed again: internal eMMC became mmcblk0, TF mmcblk1; partition identity checks are mandatory.

Still required: repeatable modern boot with storage, standard26.10 systemd PID1 probe,
display/touch/backlight, PM8921 charging/BMS/temperature, Wi-Fi, local touch management,
full rootfs installation and oldOS removal, cold boots/restarts, screen-off server
continuity and the approved24-hour stability run. No CI/unit result substitutes for these.

Private full hardware logs contain identifiers and stay outside this public tree.

## Actual Ubuntu26.10 PID1 probe (2026-10-21)

- CI [39532334532](https://github.com/yys235/l36h-ubuntu-touch/actions/runs/39532334532) built the signed-input ARMhf RAM rootfs. Downloaded archive size49,711,341bytes and SHA256 c7f5e94d006e10aad031962d3ae5c313d4943c2d30ddec622335f6c95c69cdd1 matched its manifest.
- Third diagnostic boot used the corrected DTB and handoff-capable initramfs. Boot image SHA256 74bfbf657973902266a02a8986de7c2c2499d682a4bb41d8be01e43097947f73.
- Rootfs and installer public key were downloaded and hash-checked in RAM. Host keys were generated on the phone. Diagnostic PID1 executed switch_root into actual Ubuntu systemd.
- SSH on port22 authenticated the installer public key. Actual `/proc/1/exe` was `/usr/lib/systemd/systemd`, `/proc/1/comm` was `systemd`, `/etc/os-release` reported Ubuntu26.10, and `systemctl is-system-running` reached `running`. There were zero failed units and no pending jobs; the journal confirmed udev coldplug and yuga-probe.target completed.
- An early SSH session showed a booting/nologin notice while startup was still in progress. Root key login worked. The RAM probe lacks a configured locale and real-time clock correction; these remain production configuration work. Explicit cgroup2 mount evidence still needs capture in the next probe; systemd startup alone is not that check.
- Recovery boot source and full-length boot-partition readback SHA256 matched before reboot. Old3.4 diagnostic environment returned and reported Charging. No system/userdata/TF filesystem was formatted or installed by this RAM probe.

This proves standard systemd and SSH can run on this phone with the modern kernel. It does not complete display, touch, charging, Wi-Fi, local UI, persistent installation or stability acceptance.
