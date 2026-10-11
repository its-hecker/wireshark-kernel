# WireShark kernel — Pixel 4 / Pixel 4 XL

One AnyKernel3 ZIP for **Pixel 4 (`flame`) and Pixel 4 XL (`coral`)**, targeting Android 17 Lineage-based ROMs with a compatible floral kernel/module ABI. The default source branch is `cnb-optimized`; `cnb` remains the unchanged baseline. Every artifact includes the resolved `floral_defconfig`, KernelSU settings and provenance.

Maintainer: **Hecker (@its-hecker)**. Installation displays the maintainer, repository, [updates channel](https://t.me/pixel4seriesupdates), target ROM family and detected device.

## Compatibility

Both devices use the shared `floral_defconfig`, boot header v2, a DTB in boot and an 8 MiB DTBO partition. The ZIP preserves the complete floral DTBO table and its ordering, including prototype/EVT/DVT/production variants. Validation requires the production coral/flame overlays and their correct board IDs.

The baseline floral configuration matches LineageOS `lineage-24.0` kernel commit `28f9290ae067d3e7857126eb6312720dbe9c7c80`; WireShark adds its existing ThinLTO, WireGuard and KernelSU settings. Lineage's shared device tree (`6a4ad9f39145ba7c6ff927041b6e9ff453edc1f8`) uses the same kernel/boot layout. This source/configuration comparison does **not** establish that every ROM's compiled drivers match.

**Module ABI preflight runs before any partition write.** Every module built with this kernel must be readable on the ROM. A static ARM64 checker verifies its name, vermagic feature flags, module structure size and legacy Clang CFI mode. Every imported symbol CRC must match the freshly built kernel's complete `Module.symvers`; exported symbol names/CRCs must match the built reference. Different compiler versions and file hashes are accepted only when these checks pass.

Linux ignores the release-name part of vermagic for versioned modules. The preflight follows that rule: a compatible Lineage `4.14.357-openela` module is not rejected solely because the target release is `4.14.357-WireShark+`. Feature flags, a nonempty symbol-version table and `module_layout` are still required. The optimized source also restores normal runtime rejection of mismatched symbol CRCs, removing the old CRC bypass.

Missing/unreadable modules produce a Vendor-mount diagnostic; actual ABI failures identify the incompatible symbol/metadata and stop installation. Vendor is read only. The ZIP does not replace ROM modules; `module-reference/` files are for validation. A matching module archive is included separately for ROM developers.

No ROM-brand restriction is used, and the installer does not infer the installed Android version from recovery. **Android 17 alone does not establish compatibility.** Passing preflight is not a phone boot test. A ROM with a different driver ABI needs a corresponding kernel/module build. Phone boot and hardware tests remain pending on both devices.

## Build

Open **Actions → Build WireShark → Run workflow**, or push a build-script change to `main`. After success, download **`WireShark-floral`** and extract the outer artifact ZIP. The inner **`WireShark-floral-<kernel-commit>.zip`** is flashable. SHA256, kernel/builder/tool revisions, resolved configuration and matching modules accompany it.

The Android 13 AOSP Coral workspace supplies the original Clang toolchain; this does not restrict the Android userspace version. Wi-Fi and touch drivers build from the bundled source. Packaging checks all built references against actual exports, the static ARM64 checker and both production overlays.

Regression coverage includes 29 module ABI/installer cases and 8 tests compiling the actual optimized kernel CRC/vermagic functions. Cases cover compatible Lineage release names, changed ABI rejection, coral/flame acceptance, recovery property fallback, unsupported devices and maintainer output.

The shared floral build succeeded in [run 38161422852](https://github.com/its-hecker/wireshark-kernel/actions/runs/38161422852), using builder `d8109a051e1b3c8f3da8e58f903e6033a3e7e4fd` and source `ad869a2e1f74090fea2ff402d1261e9206ba13cd`. [Download the WireShark-floral artifact](https://github.com/its-hecker/wireshark-kernel/actions/runs/38161422852/artifacts/11711555318) and extract **`WireShark-floral-ad869a2e1f74.zip`**. Its SHA256 is `da3f793e5d34cd74686e2e30ec96251467ccadb2b920a2f7eea926eb89610e66`. Downloaded-artifact verification passed: ZIP/checksum integrity, both production overlays and device guards, all 27 built references and the uploaded InfinityX ADSP module against this build's actual exports (all 28 imports). Phone flashing and full boot/hardware testing remain pending.

The earlier coral correction succeeded in [run 38093277412](https://github.com/its-hecker/wireshark-kernel/actions/runs/38093277412); the uploaded InfinityX Clang 22 `adsp_loader_dlkm.ko` passed all 28 imported CRCs against that build, including `__stack_chk_guard`. That artifact remains coral-only. Use the new `WireShark-floral` artifact for the shared installer. A fresh build and phone boot tests are separate from that earlier driver check.

## Installation

Use an unlocked Pixel 4 or Pixel 4 XL with a recovery/root kernel installer supporting AnyKernel3. Flash the inner ZIP on a ROM whose modules pass preflight, then reboot.

The installer detects coral/flame and the active A/B slot, backs up boot/DTBO to `/sdcard/WireShark-backups`, and repacks the installed boot while preserving its ramdisk. It installs the kernel, DTB and complete floral DTBO table into that slot. It does not wipe data or flash the other slot.

Backups are partition images. Restore the recorded slot with `fastboot flash boot_a <backup>` or `boot_b`, and similarly `dtbo_a` or `dtbo_b`. Use backups from the same device and ROM.

## Optimizations and features

Three adapted Sultan fixes detect wakeups when freezing just completed, preserve wakeups from suspend callbacks and avoid repeated s2idle wake calls. Details/tests are in `docs/wireshark-optimization.md` and `tests/suspend_wakeup_host.py`. CPU/GPU clocks, thermal controls and scheduler are unchanged. ThinLTO reduces linker pressure on hosted runners; CFI and shadow call stack remain enabled. Battery/frame-time improvements require hardware measurements.

**Known limitation:** KernelSU-Next pin `7d7f214e53d1b229115f094be4fe714601313027` lacks SUSFS Kconfig definitions. Configuration normalization drops those settings, so **SUSFS is inactive**. Enabling it requires a compatible KernelSU/SUSFS integration.

## Repository and sources

- `main`: workflow, installer, packaging and validation.
- `cnb`: unchanged complete baseline source.
- `cnb-optimized`: complete source, Sultan adaptations, ThinLTO and restored module CRC rejection.
- Import origin: https://github.com/its-hecker/infinity_cnb_kernel_google_msm-4.14; exact revisions in `scripts/import-source.sh`.
- Lineage baseline: https://github.com/LineageOS/android_kernel_google_msm-4.14 and https://github.com/LineageOS/android_device_google_coral.
- Build manifest: https://android.googlesource.com/kernel/manifest/ (`android-msm-coral-4.14-android13`).
- Installer: https://github.com/osm0sis/AnyKernel3; pinned revision and upstream license retained.

Source branches are imported once and never overwritten by subsequent workflows. Kernel development belongs on `cnb-optimized`. Kernel licensing is GPL-2.0 with source-specific notices; licenses, KernelSU submodule references and optimization attribution are retained.

