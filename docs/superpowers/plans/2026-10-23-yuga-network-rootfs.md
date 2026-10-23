# Yuga Ubuntu network rootfs probe implementation plan

> **For agentic workers:** Use superpowers:executing-plans in this existing worktree. This implements the already approved server architecture; no new architecture approval is required.

**Goal:** Validate Ubuntu26.10 NetworkManager and public-key SSH over Wi-Fi on the actual phone, providing a working server maintenance path while USB coexistence is investigated.

**Architecture:** Extend the signed-input RAM systemd rootfs with official network packages. Keep usb0 unmanaged by NetworkManager and permit IPv4 SSH22 with public-key-only root authentication. Inject any private Wi-Fi profile and installer public key only in the private bounded hardware probe, never into public artifacts.

**Tech stack:** Ubuntu26.10 ARMhf, systemd261, NetworkManager, wpa_supplicant, OpenSSH, Python3 standard library, existing remote CI and guarded diagnostic boot.

**Spec:** `C:/Users/MSIK/Documents/ChatGPT/L36H 刷UT-GPT/docs/superpowers/specs/2026-10-20-yuga-ubuntu-server-design.md` (approved2026-10-20).

## Global constraints

- Full latest Ubuntu reinstall and local screen Wi-Fi/device information remain the end goal; a RAM network probe does not complete it.
- Standard systemd is actual PID1, not a chroot substitute.
- Official Ubuntu packages retain signed APT verification and fixed Base signature/hash validation.
- SSH22 uses installer public keys, no shared password, no public host private keys.
- Camera, display, charging, screen-off continuity and24-hour acceptance remain separate pending gates.
- Do not format TF or touch TA, bootloader, modem/calibration partitions. This probe does not format OS data partitions either.
- Modern experiments remain bounded and prewrite/readback-verify the old charging diagnostic recovery image.

## Review focus

- An IPv4 LAN listener must not weaken root authentication: verify actual ARM sshd effective settings, including rejection of password authentication.
- NetworkManager must leave the existing USB address alone: inspect its effective configuration and actual usb0 state.
- Generic rootfs must contain no Wi-Fi PSK/profile, installer identity or host private key.
- Private profile input may have absent credentials, unsupported enterprise security, escaped SSIDs or duplicate keys: fail without printing secrets and preserve supported personal-network data.
- A phone with all-zero wireless MAC needs a unique valid address before interface-up; test address bits/determinism and prove runtime interface-up.

## Task1: Generic networking rootfs and SSH policy

**Files:** create `server/modern-boot/configure-network-probe.py`, test `tests/test_network_probe.py`; modify `build-systemd-probe.sh`, `validate-probe-sshd.py`, `tests/test_probe_sshd.py`, existing rootfs workflow artifact evidence list.

**Interfaces:** `configure(root: Path)` installs generic NM configuration and the probe target drop-in. `validate(text, listen_address='172.16.42.1:22')` retains old USB-policy validation; CLI `--network` validates0.0.0.0:22 instead. Current builder produces a new network-capable revision with a distinct manifest/hash; retain earlier immutable rootfs inputs.

- [ ] Add failing tests for generic configuration: NM unmanaged usb0, target starts NM, SSH IPv4 LAN listener/public-key policy, no credential/profile/host-key files created.
- [ ] Add failing effective-policy tests accepting LAN key-only and rejecting LAN password authentication or duplicate listeners.
- [ ] Implement the configuration writer and validator parameter.
- [ ] Add official network-manager, wpasupplicant, iw and python3-minimal to the CI rootfs, apply generic configuration before effective-policy validation.
- [ ] Run all tests under WSL Linux, shell syntax checks and diff checks; update source manifest.
- [ ] Commit/push development branch, dispatch the existing rootfs workflow once. Verify target ARM commands and metadata from that exact run; do not restart a live run on observation timeout.

## Task2: Private network input and handoff preparation

**Files:** create `server/modern-boot/prepare-probe-network.py` and meaningful parser/address tests if a saved personal-network profile is available. Private evidence stays under audit-artifacts or the existing private access directory.

**Interfaces:** `prepare_profile(text: str, serial: str) -> str` accepts a supported NM personal-network keyfile and returns a normalized DHCP/autoconnect profile with a stable locally administered MAC. CLI writes a new private0600 file and prints no credential content.

- [ ] Locate only saved NM profile paths in identity-verified userdata mounted read-only/noload; do not dump credential values.
- [ ] Test supported WPA-PSK/SSID preservation and deterministic unicast/local MAC; reject missing/invalid credentials, unsupported enterprise security, duplicate keys and multiline injection without reflecting secrets in errors.
- [ ] Implement minimal normalization, keeping public output credential-free. Use a fresh profile UUID, remove old hardware-MAC/BSSID binding, retain the requested SSID/security.
- [ ] Prepare validated installer public key and profile for private RAM injection; enforce0600/owner0 on the phone.
- [ ] Review the whole networking change and fix actionable issues before runtime use.

## Task3: Bounded real networking verification

**Files:** private diagnostic scripts/logs; update public `VALIDATION.md` and `HARDWARE-BRINGUP.md` with credential-free conclusions only.

- [ ] Verify exact CI artifact manifest/signatures and boot/module match. Prewrite/readback-verify recovery boot.
- [ ] Download the generic rootfs in RAM before WCNSS disables USB; inject private inputs without logging secrets, arrange bounded fallback, then actual switch_root/systemd.
- [ ] Let NetworkManager bring up the valid-address Wi-Fi profile; save state/IP/journal to TF with bounded logging.
- [ ] Verify LAN SSH22 using installer key, actual PID1/systemd/NM/device state, and a small network transfer. Do not claim association or reliability from scan results.
- [ ] Return to old charging diagnostic within the current experiment limit, verify charging/temperature and unmount TF.
- [ ] Record exact pass/fail and remaining full-install gates; do not mark the overall goal complete.
