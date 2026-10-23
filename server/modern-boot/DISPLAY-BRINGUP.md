# Yuga display probe (not hardware-validated yet)

The recovery kernel identifies Sharp LS050T3SX01, controlled by Renesas R63311.
Legacy RGB output was physically confirmed on 2026-10-23 after retaining an open
framebuffer descriptor and explicitly panning. Closing the final descriptor powers
the legacy panel off. This proves a working reference, not modern DRM support.

The fixed modern source has no Yuga panel graph or matching panel driver.
`install-display.py` installs a diagnostic driver, verifies SHA256 of each
modified upstream C/build file, rejects ambiguous board wiring, and validates all
inputs before writing. The source version remains pinned by `inputs.json`.

Sony GPLv2 reference at kernel base `3e373fec12898bacbcb93713732dbc26f5b3b3f5`:

- `drivers/video/msm/mipi_dsi_panel_r63311_sharp_ls050t3sx01.c`, SHA256
  `d98ba2d107487639215c76a0b4a138bef1d18617cf78d1065ddb8e68e1217986`.
- `arch/arm/mach-msm/board-sony_fusion3-display.c`, SHA256
  `91b4111fe3c9f78bea7c8b61a0b67488baa35539830b7d775a075b6be071ef85`.
- `arch/arm/mach-msm/board-sony_fusion3_yuga.c` for LM3533 settings and
  `board-sony_yuga-pmic.c` for S4-powered GPIOs.

Panel: 1080x1920 RGB888, four DSI lanes, 60 Hz; horizontal front/pulse/back
134/16/64 and vertical 4/2/4. Pixel clock is 149845 kHz. Supply L29 is 1.8 V,
L2 is 1.2 V. Reset is PM8921 GPIO25, active low; DCDC is GPIO24, active high.
Only Yuga's v2 DSI host gets a private configuration without the absent avdd
rail. It enables L29, waits 25 ms, then enables L2; panel prepare raises DCDC,
holds reset for 25 ms, releases it for 11 ms, exits sleep and waits 150 ms.
Gamma and display-on are sent in panel enable, after video starts, matching
the dlogo panel's requirement. Disable sends display-off/20 ms then sleep/100 ms;
unprepare asserts reset/11 ms and lowers DCDC/25 ms before host rail teardown.

LM3533: GSBI1 I2C address 0x36, PM8921 GPIO26 HWEN, boost 500 kHz/24 V,
bank A 20200 uA, linear mapping, PWM disabled, both HVLED outputs on bank A
with their anodes routed to CPOUT (register 0x25 bits 0 and 1).
The integration reuses mainline MFD/backlight drivers and adds fixed board data
only for `sony,yuga-lm3533` on Yuga. ALS and RGB banks are not initialized.
DRM manages the backlight through the standard class so blanking can set actual
brightness to zero. A low initial brightness of 20 is a probe policy, not a new
hardware limit. The 3D GPU is disabled in the diagnostic DT; scanout and the
planned software-rendered local UI do not require acceleration.

Panel, MFD and backlight drivers are modules. Load them only after USB logging
is available. The first experiment must leave WCNSS stopped, stage and verify
the known recovery boot partition, and use bounded watchdog recovery. Check
panel logs, DRM modes, framebuffer output, physical image, repeated blank/wake,
and uninterrupted maintenance commands. A successful build or the legacy RGB
test does not satisfy these hardware acceptance gates.
