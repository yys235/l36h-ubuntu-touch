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

Source inspection shows the IRQ0 rejection exits before `rmi_enable_sensor()`, which synchronously configures functions and processes pending interrupts. Build39538605466 makes RMI4 core/I2C modular so USB logging can be established before probe. Delayed module loading on hardware completed IRQ initialization, function configuration and pending-interrupt processing with ret=0, registered TM2282-001 and event2, and retained SSH access. Physical touch events and repeated cold boots remain unverified.

## Battery measurement preparation

The diagnostic build also prepares PM8xxx XOADC and IIO hwmon as modules for a later bounded telemetry probe. The Sony Yuga regulator source maps `vreg_xoadc` to L14 at1.8V, not L18. The fixed modern board currently lacks the ADC's `xoadc-ref-supply` link; this must be supplied explicitly in the test DTB before loading the ADC driver. Raw or calibrated ADC readings are not proof of a functional charger/BMS or safe unattended charging.

## Wireless failure evidence

The modular kernel build39538605466 completed successfully; its matched artifact manifest and all selected module ELF structures were verified. WCNSS probes logged PAS init_image returning0 before the USB command channel disappeared. Two systemd probes occurred near the automatic deadline, so those runs cannot establish a firmware fault or successful hang recovery by themselves. A subsequent initramfs-only probe armed a fresh watchdog before wireless startup and still required physical recovery after more than four minutes without a command channel. Normal stop-feeding testing did restore the old diagnostic kernel, but recovery from the actual wireless failure is not reliable.

Sony's downstream regulator map assigns PM8921 S3 to both riva_vddcx and HSUSB_VDDCX (also CPU digital votes). This is a source-backed shared-rail observation, not a demonstrated cause. The modern driver also contains unbounded IRIS status polling. Additional begin/end traces around MDT load, regulator/IRIS enable, IRIS configuration, secure authentication/reset and resource release preserve the original operations and return values, allowing the next probe to identify the failing boundary before changing power policy.

## Camera exclusion

The server kernel build explicitly disables MEDIA_SUPPORT and checks the effective Kconfig result after olddefconfig. DRM display support is separate and remains enabled. This implements the requested camera exclusion for subsequent builds; the already running wireless diagnostic CI39574233322 predates this configuration change and is not evidence that the new constraint has passed a kernel build or hardware test.

## TF-backed WCNSS evidence

CI39574233322 completed successfully. Persistent synchronous TF logs show all seven traced WCNSS boundaries complete, authentication/reset returning0, remoteproc running, WCNSS Version1.5 1.2 and wlan0 creation. The firmware-start syscall returned0 and heartbeat continued despite USB command loss. Two explicitly armed60-second deadlines and automatic returns to the old charging diagnostic were observed. These are evidence of successful firmware startup and a surviving CPU, not working USB/Wi-Fi coexistence or verified Wi-Fi scanning/connection.

A controlled derivative adds only regulator-always-on to `/soc/rpm@108000/regulators/s3`; sorted decompiled DTB comparison contains exactly that one additional property. Voltage constraints, kernel and modules are unchanged. This derivative also lost USB commands, so S3 always-on alone is not a fix. Continue with USB state/address/counter and clock/regulator snapshots, rather than treating the shared-rail hypothesis as established.
