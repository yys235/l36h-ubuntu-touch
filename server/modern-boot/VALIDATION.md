# Modern boot validation status

This is a hardware bring-up branch. Ubuntu26.10 is not yet installed as a complete server.

- Fixed APQ8064 kernel CI [39398776562](https://github.com/yys235/l36h-ubuntu-touch/actions/runs/39398776562): passed, Linux7.2.0-yuga-modern-probe, Clang18.1.3.
- All downloaded artifact sizes/SHA256 independently verified.
- 13 existing test suites and 26 initial new boot/input/initramfs tests passed; two added GPIO26 tests now bring the new total to28.
- Independent code review found no actionable issue before the first hardware flash.
- First hardware boot: actual uname7.2.0-yuga-modern-probe, four CPUs, approximately2GiB RAM, Windows RNDIS driver bound, DHCP assigned host172.16.42.2, phone172.16.42.1 private telnet executed commands.
- eMMC and GPT detected. Internal storage is mmcblk1 in this kernel, whereas old3.4 used mmcblk0. Installation must resolve partition identity and size, not reuse device numbers.
- TF probe failed with GPIO26 pin ownership conflict. Controlled DTB derivative removes only `function="gpio"` from the card-detect pinconf node, preserving pinconf and GPIO descriptor handling. Kernel/modules remain identical to CI; derivative provenance is explicit. Sorted decompiled DTB diff contains exactly that one removed property. Follow-up review found no concrete issue; second hardware test pending.
- First diagnostic boot had only DRM device, no panel/fb, no touch input, no power_supply entries; SoC thermal readings were available. Wi-Fi firmware was absent. These are incomplete hardware support, not completed server functionality.
- First experiment ended within five minutes. Old diagnostic boot was restored by checking boot PARTNAME/size, validating source SHA256 and matching a complete-length readback SHA256. Old3.4 uname and charging were confirmed afterward.
- Second hardware boot with GPIO26 fix: Windows RNDIS/DHCP/telnet worked; eMMC mmcblk1 and64GB SDXC mmcblk0/p1 detected, previous GPIO ownership error absent. The run ended around135seconds, recovery boot source/readback hashes matched before reboot. A repeat of this corrected configuration remains before PID1 handoff.

Still required: repeatable modern boot with storage, standard26.10 systemd PID1 probe,
display/touch/backlight, PM8921 charging/BMS/temperature, Wi-Fi, local touch management,
full rootfs installation and oldOS removal, cold boots/restarts, screen-off server
continuity and the approved24-hour stability run. No CI/unit result substitutes for these.

Private full hardware logs contain identifiers and stay outside this public tree.
