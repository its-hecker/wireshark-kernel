# WireShark kernel — Pixel 4 XL

Build and package the kernel source in this repository as an AnyKernel3 ZIP for **coral only**. The default source branch is `cnb-optimized`; select `cnb` under Run workflow to build the unchanged baseline. KernelSU/SUSFS settings come from the source's `floral_defconfig`; this repository does not change them.

The initial optimization set adapts three Sultan suspend/wakeup fixes: detect wakeups even when freezing just completed, preserve wakeups from suspend callbacks, and avoid repeated s2idle wake calls. Source details and host regression tests are in the kernel branch's `docs/wireshark-optimization.md` and `tests/suspend_wakeup_host.py`. CPU/GPU clocks, thermal controls, scheduler and defconfig are unchanged. No battery or frame-time improvement is claimed until measured on hardware.

## Repository layout

- `main`: build workflows, AnyKernel3 installer, packaging and validation scripts.
- `cnb`: complete baseline kernel source.
- `cnb-optimized`: complete kernel source with the initial Sultan suspend/wakeup adaptations.

The workflow imports pinned source trees once, preserving licenses, KernelSU submodule references and optimization attribution. Existing source branches are never overwritten on subsequent runs. Both build choices clone this repository; further kernel development belongs on `cnb-optimized`.

## Build

Open **Actions → Build WireShark → Run workflow**, or push a build-script change to main. Download the `WireShark-coral` artifact when the run succeeds. Extract the outer GitHub artifact ZIP: the inner `WireShark-coral-<commit>.zip` is the flashable ZIP. A SHA256 file, source/tool provenance, build config, and matching module archive are included alongside it.

The first build is experimental until tested on a phone. This is not a universal Android 17 kernel. The Android 13 AOSP Coral kernel build workspace supplies the original build tools and external drivers; ROM compatibility depends on the ROM's kernel/module ABI, not its Android version alone.

## Installation

Use an unlocked Pixel 4 XL and a recovery or root kernel installer that supports AnyKernel3. Keep a known-good boot image and a way to restore it with fastboot. Flash the inner ZIP on the compatible ROM, then reboot.

The installer checks `coral`, determines the active A/B slot, backs up its boot and dtbo partitions to `/sdcard/WireShark-backups`, and repacks the existing boot image while preserving its ramdisk. It installs the built kernel, DTB and DTBO only into the active slot. It does not wipe data or flash the other slot.

**Module compatibility is enforced before any partition write.** Every module built with this kernel must already exist on the ROM with the identical SHA256 hash. If a module is missing or differs, installation aborts. This deliberately strict check prevents silently installing a kernel against unmatched Wi-Fi or other vendor drivers. The matching module archive is for ROM developers to integrate into their ROM; it is not itself a flashable ZIP. Do not disable the guard to force installation on another ROM. Different build environments can produce different module hashes even with compatible source, so an abort requires investigation rather than proving an ABI mismatch.

Backups are partition images, not data backups. To restore boot use `fastboot flash boot_a <backup>` or `boot_b`, matching the recorded slot; similarly restore `dtbo_a` or `dtbo_b` if needed. Never flash an image from a different device or ROM.

## Sources and licensing

- Kernel source: this repository's `cnb` and `cnb-optimized` branches (GPL-2.0 and source-specific notices)
- Import origin: https://github.com/its-hecker/infinity_cnb_kernel_google_msm-4.14; exact source revisions are recorded in `scripts/import-source.sh` and the import commits
- KernelSU-Next: the source repository's pinned submodule
- Build manifest: https://android.googlesource.com/kernel/manifest/ branch `android-msm-coral-4.14-android13`
- Installer: https://github.com/osm0sis/AnyKernel3 (upstream license retained in ZIP)

Build output records exact kernel, submodule, manifest-project and installer revisions. Consult the original source repositories for their licenses.
