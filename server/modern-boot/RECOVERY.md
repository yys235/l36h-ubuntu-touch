# Diagnostic boot recovery

These images are diagnostic experiments, not a completed Ubuntu installation.
The current boot partition was not read back successfully: there is no claim that
the original installed boot is backed up.

The retained interactive recovery image is `boot-yuga-final-kernel-diagnostic.img`,
SHA256 `bc3f36da914fa332cf4524cc3e73a7c32650e3f1621f7907c76023f02ed4c7a4`.
It starts the old 3.4 diagnostic environment; it does not restore the original UT
desktop. Keep this file and fastboot available outside the phone.

If the new kernel cannot provide a working command channel within five minutes,
return to fastboot: hold power+volume-up until three vibrations, unplug USB, then
hold volume-up while reconnecting. Verify the actual serial with `fastboot devices`.
Flash only the checked recovery image to `boot`, then reboot. TA, bootloader,
baseband and calibration partitions are not operating-system installation targets.

The RAM diagnostic telnet shell is bound to the private USB address 172.16.42.1.
It must not be exposed to Wi-Fi or preserved as a production service. The final
server uses OpenSSH on port 22.

User explicitly requested starting tests without waiting for a battery percentage.
Keep charging/thermal protection, inspect available voltage/temperature readings,
and keep experiments short while charging support is unverified.

The approved migration goal is now a full reinstall without retaining existing
phone user data. This removes backup requirements, not the need to identify the
correct partitions and verify a viable new kernel/rootfs before calling it installed.
