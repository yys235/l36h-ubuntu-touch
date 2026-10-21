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

A second isolation changed only the L17 constraints to3V with no sensor child; USB and I2C still worked. A third isolation also enabled L17 permanently for the bounded probe. The regulator summary showed use_count1 at3V; targeted sensor reads returned0x00 and0xa1. Creating an I2C `rmi4_i2c` client manually after the USB shell was established identified Synaptics TM2282-001, firmware1286791. With no IRQ assigned to that manually created client, the core rejected request_irq(0) with EINVAL without losing the shell. This proves basic power, bus and RMI descriptor communication, not working touch input. Full-DT GPIO6 interrupt setup/probing remains the next isolation boundary. Recovery boot source/readback hashes matched before ending the probe.

Modern restart2("bootloader") currently restarted normally into the prewritten old diagnostic boot rather than exposing fastboot. The same static helper from the old3.4 diagnostic then entered fastboot successfully. Production reboot-mode support remains to be checked.

## IRQ boundary isolation

The full touch DTB with only its `interrupts` property removed booted normally and identified TM2282-001 from its DT node, then rejected IRQ0. In that boot GPIO6 was input/high/function0 with pull-up. Explicitly exporting GPIO6 and requesting a falling-edge sysfs IRQ succeeded (msmgpio6, zero events observed) while USB remained responsive. The GPIO request was cleaned up before reboot. These tests narrow the issue to successful RMI IRQ initialization and subsequent sensor configuration/interrupt processing; they do not establish that changing trigger polarity is the fix.

Source inspection shows the IRQ0 rejection exits before `rmi_enable_sensor()`, which synchronously configures functions and processes pending interrupts. The next diagnostic build will make RMI4 core/I2C modular so USB logging can be established before probe. `trace-touch.py` adds begin/end messages around IRQ initialization, function configuration and pending-interrupt processing while preserving call order and return results. Its source guards reject changed/duplicate or already instrumented code. This instrumentation has not yet run on hardware.

## Battery measurement preparation

The diagnostic build also prepares PM8xxx XOADC and IIO hwmon as modules for a later bounded telemetry probe. The Sony Yuga regulator source maps `vreg_xoadc` to L14 at1.8V, not L18. The fixed modern board currently lacks the ADC's `xoadc-ref-supply` link; this must be supplied explicitly in the test DTB before loading the ADC driver. Raw or calibrated ADC readings are not proof of a functional charger/BMS or safe unattended charging.
