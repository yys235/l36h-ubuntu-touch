# Working Ubuntu Touch hardware reference

User instruction, 2026-10-23: use the already working Ubuntu Touch drivers,
configuration and fixes as the reference for every migrated subsystem.
The final target remains the approved modern kernel and standard Ubuntu server,
including local Wi-Fi/device information UI and continuous screen-off operation.

Use the complete exported working tree, not only its upstream HEAD:

- Base `3e373fec12898bacbcb93713732dbc26f5b3b3f5`, archive SHA256
  `0880b3bfc246e0c3ae782f9221ebde28e48275e6af03845c2326f3e1a622f2b2`.
- `kernel/yuga-final-working-tree.patch`, SHA256
  `1347413d36ea67807fcdc7a382bdd1cf0f41ec6f4d11cede69f2b79f3915526b`.
- `kernel/yuga-final.config`, SHA256
  `291f69b0ef18c53c8018b35fbbaeaf89627216b7ab7c3c71368c1c5f51fa06f6`.
- Overlay services under `overlay/`, including physical backlight routing,
  server-awake policy, upower compatibility and SMD Bluetooth initialization.
- Original workspace investigations `docs/power-key-backlight-investigation.md`,
  `docs/ut-server-stability.md`, and hardware readiness/source inventories.

| Subsystem | Working UT behavior and source | Modern mapping and verification gate |
| --- | --- | --- |
| Panel | Actual Sharp LS050T3SX01 dlogo/R63311. Sony `mipi_dsi_panel_r63311_sharp_ls050t3sx01.c`, `mipi_dsi_panel_driver.c` and `board-sony_fusion3-display.c`. Preserve supplies, reset delays, lane mapping, porches, sleep/gamma/display commands, and **HS TX after video starts**. | DRM panel and Yuga host rail sequencing. Modern PLL rounding must match the real divider; see `DISPLAY-BRINGUP.md`. Actual image, console text and repeat blank/wake remain required. |
| Backlight | Physical endpoint is LM3533, not the generic framebuffer brightness endpoint. User physically confirmed LM3533 zero extinguishes light and power key/wake works. Board GPIO26, I2C 0x36, bank A 20200 uA, both HVLEDs, CPOUT route, linear/PWM/boost settings. | Bind standard backlight class directly to the real LM3533. Port the endpoint behavior, including physical zero and wake brightness; the old repowerd bind mount is an implementation reference. |
| Touch | Working tree adds `INPUT_PROP_DIRECT` to clearpad. GSBI3 0x2c, GPIO6 falling edge, L17 3.0 V and S4 1.8 V. Actual old diagnostic reports module 0x41/rev0x0a, TM2282-001. Sony's board uses 1080x1920 and no axis flip for this module. | RMI4 F11/F12 share the modern 2D input framework, which uses `INPUT_MT_DIRECT` for touchscreen/default rather than touchpad. Verify actual properties, coordinate range, orientation and physical touches after delayed module load; device registration alone is insufficient. |
| Wi-Fi | Sony board `qcom_wcnss_pdata.has_48mhz_xo=1`, exact RIVA/IRIS supplies and firmware/calibration inputs. Preserve stable per-device identity and network behavior. | Pinned WCN3660 IRIS data also selects `use_48mhz_xo=true`; a generic CXO clock label by itself is not evidence of the wrong oscillator mode. Modern scans succeeded, but USB coexistence and association remain unresolved. Compare the complete old power/firmware sequence before changing shared rails. |
| Charging/BMS | `board-sony_yuga-pmic.c`, Sony battery data, PM8921 charger/BMS/ADC/CCADC, temperature thresholds and termination/safety behavior. Old USB CURRENT_MAX is reported in mA, unlike the usual microamp convention; BMS current sign also differs. | Implement actual PM8921 power-supply, calibrated temperature and charging protection. Normalize interface units deliberately. ADC binding is not charger completion. Long modern tests and unattended final installation require this gate. |
| Thermal | Working-tree board patch reduces thermal polling to 250 ms, limit to 60 C, hysteresis to 10 C and frequency step to 2. | Preserve this protection intent through verified modern TSENS calibration and CPU cooling. A DT threshold alone does not prove frequency throttling works. This remains required before server stress acceptance. |
| Screen-off server | UT `yuga-server-awake.service` holds the legacy Android wake lock, disables autosleep and masks system sleep targets; power key only controls display/backlight. | Standard Ubuntu must retain uninterrupted SSH/network/service activity with display off. Map policy to available modern suspend/logind interfaces and the local display controller; verify repeated off/on with unchanged boot and service continuity. |
| eMMC/TF | Old ext4 TF test completed 17.375 GiB checked I/O over two hours in one documented round. Partition identity and card contents are known. | Reverify SDHCI/ext4, concurrent I/O, swaps if enabled, mount/reboot persistence and soak on the new kernel. Follow the approved migration rule preserving TF contents; identify partitions before writes. |
| Bluetooth | Working-tree SMD/HCI changes and `overlay/userdata/yuga-port/bluetooth-init.sh`; documented BLE scanning. The old EATT workaround addressed a 3.4 kernel interface limit. | Reference controller/power/firmware behavior and verify native modern SMD/HCI and BLE. Old compatibility workarounds must be assessed against the new native interfaces. |
| Kernel/userspace compatibility | Working tree includes netlink/datagram, namespaces/stat/sysfs, Bluetooth and AppArmor backports for old userspace compatibility. | Check equivalent modern native behavior and retain regression tests for the original symptoms. Hardware sequence fixes remain device-specific; the modern kernel already has a different native API/implementation for many old compatibility gaps. |

Camera remains excluded as explicitly requested. Earlier successful individual
UT features are valid migration references; interrupted long tests and unresolved
network/panic records remain incomplete evidence. Each capability must be checked
on the new kernel before the final system is described as installed and stable.
