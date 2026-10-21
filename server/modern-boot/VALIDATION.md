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

Still required: full display/touch/backlight support, PM8921 charging/BMS/temperature, Wi-Fi, local touch management,
full rootfs installation and oldOS removal, cold boots/restarts, screen-off server
continuity and the approved24-hour stability run. No CI/unit result substitutes for these.

Private full hardware logs contain identifiers and stay outside this public tree.

## Actual Ubuntu26.10 PID1 probe (2026-10-21)

- CI [39532334532](https://github.com/yys235/l36h-ubuntu-touch/actions/runs/39532334532) built the signed-input ARMhf RAM rootfs. Downloaded archive size49,711,341bytes and SHA256 c7f5e94d006e10aad031962d3ae5c313d4943c2d30ddec622335f6c95c69cdd1 matched its manifest.
- Third diagnostic boot used the corrected DTB and handoff-capable initramfs. Boot image SHA256 74bfbf657973902266a02a8986de7c2c2499d682a4bb41d8be01e43097947f73.
- Rootfs and installer public key were downloaded and hash-checked in RAM. Host keys were generated on the phone. Diagnostic PID1 executed switch_root into actual Ubuntu systemd.
- SSH on port22 authenticated the installer public key. Actual `/proc/1/exe` was `/usr/lib/systemd/systemd`, `/proc/1/comm` was `systemd`, `/etc/os-release` reported Ubuntu26.10, and `systemctl is-system-running` reached `running`. There were zero failed units and no pending jobs; the journal confirmed udev coldplug and yuga-probe.target completed.
- An early SSH session showed a booting/nologin notice while startup was still in progress. Root key login worked. The RAM probe lacks a configured locale and real-time clock correction; these remain production configuration work. The following probe explicitly captured cgroup2 mounted at /sys/fs/cgroup with nsdelegate and memory accounting flags.
- Recovery boot source and full-length boot-partition readback SHA256 matched before reboot. Old3.4 diagnostic environment returned and reported Charging. No system/userdata/TF filesystem was formatted or installed by this RAM probe.

This proves standard systemd and SSH can run on this phone with the modern kernel. It does not complete display, touch, charging, Wi-Fi, local UI, persistent installation or stability acceptance.

## Wi-Fi bring-up follow-up

- WCNSS vendor firmware hashes and board NV SHA512 were checked against existing source inventories. iw6.17 and libnl3.12 ARMhf package hashes were verified against signed Ubuntu26.10 package indices.
- A host-side binary interchange bug truncated decompressed module files. The kernel rejected the malformed ELF; file-based interchange fixed this. An ARM module section-table/content bounds validator now gates kernel build output. The current56-test suite passes under Linux; its dpkg-query test must run on Linux rather than native Windows.
- Actual phone loading of rfkill, cfg80211, mac80211 and wcn36xx succeeded after that correction. No Wi-Fi interface has been verified yet.
- Starting WCNSS with the verified firmware causes command-channel loss. Later instrumented probes captured PAS init_image returning0. Subsequent startup is still unlocalized. Two probes overlapped the automatic deadline; a fresh-watchdog initramfs-only probe also lost communication and did not recover automatically. Normal watchdog stop-feeding had recovered successfully in a separate test, which does not prove recovery from this failure.

## Modular hardware build and remaining gates

- CI [39538605466](https://github.com/yys235/l36h-ubuntu-touch/actions/runs/39538605466) succeeded at publication commit ae4e1adf7061f3a7420ef237c6a65b08ed4bd9b0. Downloaded ZIP and matched kernel/DTB/module manifest hashes were checked;555 module ELF structures passed the build verifier.
- Delayed RMI4 loading on that build identified TM2282-001 and registered event2. IRQ setup, function configuration and pending-interrupt handling each returned0 while SSH remained available. Physical input events and repeat cold-boot reliability remain unverified.
- No modern power_supply/charger support has been established. Bounded experiments return to the old diagnostic environment with charging confirmed; do not infer charging support from ADC modules or the USB connection.
- Diagnostic build [39574233322](https://github.com/yys235/l36h-ubuntu-touch/actions/runs/39574233322), publication commit b706983d5853e1d7983a56329f9e25bc9e625b80, completed successfully. Artifact ZIP SHA256 fd021ede40cba3048150d9cf100b92dba7fb25cbcd3aa66ee95b9d091a7951cf and all manifest entries were verified. It adds seven WCNSS startup-boundary traces.
- Phone storage inventory confirms approximately16GB eMMC and64GB ext4 TF. Hardware diagnostic logging may mount the identity-verified TF synchronously to retain kernel messages and heartbeat across USB loss. This is a separate follow-up from the completed no-storage-mount RAM systemd probe, not a rootfs installation.

The complete Ubuntu reinstall, camera exclusion, local screen Wi-Fi/device-information interface, reliable charging, Wi-Fi, cold boot/reboot, screen-off server continuity and24-hour stability acceptance remain outstanding. The old OS data partitions have not been formatted or replaced.

## Persistent wireless diagnostics

The matched traced kernel was booted with identity-checked ext4 TF logging, using synchronous writes for kernel messages and runtime heartbeat. The command channel disappeared during WCNSS startup, but the saved logs show MDT load, regulator/IRIS enable, IRIS configuration and secure authentication/reset all completed successfully. Resource release completed, remoteproc reached running, firmware reported WCNSS Version1.5 1.2, and wlan0 appeared. The firmware-start syscall returned0 and CPU heartbeat continued after USB command loss. This contradicts the earlier whole-system-hang interpretation; Wi-Fi scanning/association is still untested.

The detached deadline recorded its start and firing60seconds later, successfully stopped the watchdog feeder, and the old3.4 diagnostic returned automatically with Charging and29C confirmed. A second probe changed only one DTB property, adding regulator-always-on to S3 without changing voltage constraints, kernel or modules. It also reached running/wlan0 but still lost USB commands; automatic recovery succeeded again. That one-property change does not solve the issue. USB addressing/link/counters and clock/regulator state need before/after capture before further power-policy changes.

TF logging/readback worked in these bounded probes without a reported filesystem error; this is not the required TF stability/soak acceptance. Recovery logs were read from the old diagnostic with the TF mounted read-only and noload, then unmounted. No OS-data partition was formatted or installed.

## USB state and first successful Wi-Fi scan

Before/after TF snapshots show the same USB address, connected route, MAC, carrier1 and UDC configured state after wireless startup, but USB RX/TX packet counters cease advancing. Windows retains its address, connected adapter and neighbor entry while ping times out. Captured clock/regulator summaries did not change across the startup. These observations do not yet identify the hardware/driver cause.

The initial wlan0 address was all zeros: interface-up failed with EADDRNOTAVAIL, so iw scan returned ENETDOWN. The pinned wcn36xx source only sets its permanent address when the DT local-mac-address property is supplied. A follow-up diagnostic set a valid locally administered per-device address before interface-up: address assignment, interface-up and iw6.17 scan all returned0. The saved scan contains172 BSS entries on5GHz frequencies. SSIDs/BSSIDs remain in private evidence. Association,2.4GHz scanning and connection stability remain unverified; a production address policy is still required.

A separate gadget UDC unbind/rebind returned0 but failed to restore USB enumeration: UDC was powered and carrier0 afterward. A subsequent automatic deadline recovered the old charging diagnostic. A logged L3 voltage-operation warning must be interpreted with the PHY's voltage-triplet fallback and fixed3075mV constraint; it alone does not establish a supply fault. Continue investigating initialization order/controller/PHY state before applying a permanent fix.

Two further controlled probes did not restore USB. First, unbinding the gadget before wireless startup and binding it after firmware startup/scan still left UDC powered and carrier0; scan returned0 with194 BSS entries. Second, the runtime USB parent identity was verified as12500000.usb, driver msm_hsusb and compatible qcom,ci-hdrc before unbinding/rebinding that controller and reconnecting the gadget. All three operations returned0, but enumeration remained absent; scan returned0 with167 BSS entries. Both probes automatically returned to the old diagnostic. These failures narrow the recovery options; they do not prove a root cause or a working coexistence fix.

Pinned include/linux/regulator/consumer.h confirms voltage_triplet first tries target..max and then min..max, so the L3 first-request warning alone cannot justify changing the board's voltage constraints. Next isolation should distinguish host USB/RNDIS recovery from the device PHY/controller path before further hardware-policy changes.
