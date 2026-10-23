# Yuga display bring-up

Implement the already approved modern Ubuntu server display requirement. User requested display priority on 2026-10-23; network profile work is deferred. Current recovery display is only a diagnostic reference.

1. Establish the working legacy reference: panel identity, complete power/reset and DSI command order, framebuffer lifetime/refresh, actual LM3533 bank wiring. Physical RGB confirmation achieved with open framebuffer descriptor plus pan; recovery has no fbcon.
2. Resolve the pinned modern DSI host/PHY regulator and MDP4 graph requirements against Sony source. Add fail-closed source/DT transformation tests before code. Do not copy Flo regulators, panel commands or GPIOs.
3. Add Sharp LS050T3SX01/R63311 DRM panel support and board graph, preserving video-before-display-on and error unwinding. Integrate LM3533 backlight using source-backed settings and proper backlight power blanking. Keep camera disabled. Compile matched kernel/DTB/modules and verify manifests.
4. Run a short display-only modern probe with USB logging and known recovery prewritten/read back. Keep WCNSS off to isolate display from existing USB/Wi-Fi interaction. Verify DRM connector/modes, errors, framebuffer output and physical display. Preserve bounded recovery and temperature safeguards without waiting for battery percentage.
5. Validate real console text, repeated blank/wake and server activity while blank. Only then integrate local Wi-Fi/device info UI and resume network coexistence work. Do not mark the full OS install complete from RGB or CI alone.

Acceptance: actual modern kernel produces stable readable 1080x1920 output, hardware backlight reaches zero on blank and resumes, USB/SSH remains usable during screen changes, no reboot or kernel failure. Latest Ubuntu server installation and 24-hour acceptance remain separate outstanding gates.
