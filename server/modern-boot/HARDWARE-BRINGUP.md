# Yuga local hardware bring-up

The approved server goal includes on-device Wi-Fi setup and device information. The following is experimental wiring, not a supported installation profile.

## Touch references and isolation

Sony downstream `arch/arm/mach-msm/board-sony_fusion3.c` assigns clearpad to GSBI3 I2C address0x2c and GPIO6. `drivers/input/touchscreen/clearpad_core.c` requests falling-edge interrupts. Yuga `board-sony_yuga-regulator.c` maps touch_vdd to L17 at3,000,000uV and touch_vio to S4 at1,800,000uV. The fixed modern board file instead sets L17 to2,000,000uV and does not instantiate the sensor.

`enable-touch.py BOARD OUTPUT` appends `yuga-touch.dtsi` and changes only the exact known L17 voltage node. Unknown board, pre-existing wiring and unknown voltage layouts are refused. Modern RMI4 I2C/F11/F12 are already built in. No touch firmware flashing is performed.

`--bus-only` enables GSBI3 and its I2C controller without a touch child, touch pin state, or supply voltage change. It isolates bus initialization from sensor/regulator probing.

The local compile used only DTS/bindings from the verified fixed kernel source archive. Before enabling touch, recompiling the existing corrected board produced an identical sorted decompiled tree to the already booted DTB. The touch-derived tree compiled successfully, but the first actual touch boot did not expose a USB channel. That test is unsuccessful; the fault is not yet localized. Fastboot recovery was successful. The bus-only image then booted successfully: USB diagnostic commands worked; GSBI3 reported protocol2; platform driver i2c_qup bound 16280000.i2c and created i2c-0. No deferred devices were listed. L17 remained unused at2V. One targeted read at0x2c returned NACK while the sensor supply was not enabled. This does not test powered touch or touch events. Recovery image source and full-length partition readback hashes matched before reboot.

## Remaining drivers

The fixed kernel includes LM3533 MFD/backlight source, but its core requires platform_data and has no DT parser/match table. Adding a DT node alone cannot establish a working backlight. A binding/driver adaptation or a carefully scoped board driver is still required.

No PM8921 charger/BMS power-supply driver was found in the fixed source. Existing PM8921 XOADC support is a separate subsystem; it does not establish charging support. Do not bypass charging/temperature protections while porting these pieces.
